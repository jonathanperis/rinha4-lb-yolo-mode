#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <poll.h>
#include <signal.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/epoll.h>
#include <sys/resource.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/un.h>
#include <sys/uio.h>
#include <time.h>
#include <unistd.h>

#ifndef MSG_NOSIGNAL
#define MSG_NOSIGNAL 0
#endif

#define MAX_UPSTREAMS 16
#define MAX_UPSTREAM_PATH 108
#define DEFAULT_PORT 9999
#define DEFAULT_BACKLOG 65535
#define MAX_EVENTS 1024
#define MAX_FDS 65536
#define BUFFER_SIZE 4096

typedef struct {
    char path[MAX_UPSTREAM_PATH];
} upstream_path_t;

typedef struct Conn Conn;

typedef struct {
    Conn *conn;
    int side; /* 0=client, 1=backend */
} FdRef;

struct Conn {
    int client_fd;
    int backend_fd;
    int backend_connecting;
    char c2b[BUFFER_SIZE];
    size_t c2b_off;
    size_t c2b_len;
    char b2c[BUFFER_SIZE];
    size_t b2c_off;
    size_t b2c_len;
};

static upstream_path_t g_upstreams[MAX_UPSTREAMS];
static int g_upstream_count = 0;
static unsigned int g_rr_next = 0;
static FdRef g_fd_refs[MAX_FDS];
static int g_epoll_fd = -1;

static const char *env_or(const char *key, const char *fallback) {
    const char *value = getenv(key);
    return value != NULL && value[0] != '\0' ? value : fallback;
}

static int env_int(const char *key, int fallback) {
    const char *value = getenv(key);
    if (value == NULL || value[0] == '\0') return fallback;
    char *end = NULL;
    long parsed = strtol(value, &end, 10);
    if (end == value || parsed <= 0 || parsed > 1000000) return fallback;
    return (int)parsed;
}

static int streq_ci(const char *a, const char *b) {
    while (*a && *b) {
        char ca = *a++;
        char cb = *b++;
        if (ca >= 'A' && ca <= 'Z') ca = (char)(ca - 'A' + 'a');
        if (cb >= 'A' && cb <= 'Z') cb = (char)(cb - 'A' + 'a');
        if (ca != cb) return 0;
    }
    return *a == '\0' && *b == '\0';
}

static void sleep_ms(long ms) {
    struct timespec ts;
    ts.tv_sec = ms / 1000;
    ts.tv_nsec = (ms % 1000) * 1000000L;
    while (nanosleep(&ts, &ts) < 0 && errno == EINTR) {}
}

static void set_limits(void) {
    struct rlimit limit = {65535, 65535};
    (void)setrlimit(RLIMIT_NOFILE, &limit);
}

static int set_nonblocking(int fd) {
    int flags = fcntl(fd, F_GETFL, 0);
    if (flags >= 0 && fcntl(fd, F_SETFL, flags | O_NONBLOCK) != 0) return -1;
    return 0;
}

static void tune_tcp_socket(int fd) {
    int one = 1;
    (void)setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &one, sizeof(one));
}

static int listen_tcp(int port, int backlog) {
    int fd = socket(AF_INET, SOCK_STREAM | SOCK_NONBLOCK | SOCK_CLOEXEC, 0);
    if (fd < 0) return -1;

    int one = 1;
    (void)setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));
#ifdef SO_REUSEPORT
    (void)setsockopt(fd, SOL_SOCKET, SO_REUSEPORT, &one, sizeof(one));
#endif
    tune_tcp_socket(fd);

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons((uint16_t)port);

    if (bind(fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        close(fd);
        return -1;
    }
    if (listen(fd, backlog) < 0) {
        close(fd);
        return -1;
    }
    return fd;
}

static int connect_unix_fdpass(const char *path) {
    int fd = socket(AF_UNIX, SOCK_SEQPACKET | SOCK_CLOEXEC, 0);
    if (fd < 0) return -1;

    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    if (strlen(path) >= sizeof(addr.sun_path)) {
        close(fd);
        return -1;
    }
    strcpy(addr.sun_path, path);

    if (connect(fd, (struct sockaddr *)&addr, sizeof(addr)) != 0 || set_nonblocking(fd) != 0) {
        close(fd);
        return -1;
    }
    return fd;
}

static int connect_unix_nonblocking(const char *path, int *connecting) {
    int fd = socket(AF_UNIX, SOCK_STREAM | SOCK_NONBLOCK | SOCK_CLOEXEC, 0);
    if (fd < 0) return -1;

    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    if (strlen(path) >= sizeof(addr.sun_path)) {
        close(fd);
        return -1;
    }
    strcpy(addr.sun_path, path);

    int rc = connect(fd, (struct sockaddr *)&addr, sizeof(addr));
    if (rc == 0) {
        *connecting = 0;
        return fd;
    }
    if (errno == EINPROGRESS || errno == EAGAIN || errno == EWOULDBLOCK) {
        *connecting = 1;
        return fd;
    }
    close(fd);
    return -1;
}

static void add_upstream(const char *begin, size_t len) {
    while (len > 0 && (*begin == ' ' || *begin == '\t' || *begin == '\n')) {
        ++begin;
        --len;
    }
    while (len > 0 && (begin[len - 1] == ' ' || begin[len - 1] == '\t' || begin[len - 1] == '\n' || begin[len - 1] == '\r')) {
        --len;
    }
    if (len == 0 || g_upstream_count >= MAX_UPSTREAMS) return;
    if (len >= sizeof(g_upstreams[g_upstream_count].path)) {
        fprintf(stderr, "upstream path too long\n");
        exit(1);
    }
    memcpy(g_upstreams[g_upstream_count].path, begin, len);
    g_upstreams[g_upstream_count].path[len] = '\0';
    ++g_upstream_count;
}

static void parse_upstreams(const char *fallback) {
    const char *env = env_or("UPSTREAMS", fallback);
    const char *start = env;
    g_upstream_count = 0;
    for (const char *p = env;; ++p) {
        if (*p == ',' || *p == '\0') {
            add_upstream(start, (size_t)(p - start));
            if (*p == '\0') break;
            start = p + 1;
        }
    }
    if (g_upstream_count == 0) {
        fprintf(stderr, "no upstreams configured\n");
        exit(1);
    }
}

/* ============================ fd-passing mode ============================ */

typedef struct {
    char path[MAX_UPSTREAM_PATH];
    int fd;
} fdpass_upstream_t;

static fdpass_upstream_t g_fdpass_upstreams[MAX_UPSTREAMS];

static int send_fd(int socket_fd, int passed_fd) {
    char byte = 1;
    struct iovec iov;
    iov.iov_base = &byte;
    iov.iov_len = 1;

    union {
        char buf[CMSG_SPACE(sizeof(int))];
        struct cmsghdr align;
    } control;
    memset(&control, 0, sizeof(control));

    struct msghdr msg;
    memset(&msg, 0, sizeof(msg));
    msg.msg_iov = &iov;
    msg.msg_iovlen = 1;
    msg.msg_control = control.buf;
    msg.msg_controllen = sizeof(control.buf);

    struct cmsghdr *cmsg = CMSG_FIRSTHDR(&msg);
    cmsg->cmsg_level = SOL_SOCKET;
    cmsg->cmsg_type = SCM_RIGHTS;
    cmsg->cmsg_len = CMSG_LEN(sizeof(int));
    memcpy(CMSG_DATA(cmsg), &passed_fd, sizeof(passed_fd));

    for (;;) {
        ssize_t n = sendmsg(socket_fd, &msg, MSG_NOSIGNAL);
        if (n == 1) return 0;
        if (n < 0 && errno == EINTR) continue;
        if (n < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
            struct pollfd pfd;
            pfd.fd = socket_fd;
            pfd.events = POLLOUT;
            pfd.revents = 0;
            int r;
            do {
                r = poll(&pfd, 1, 10);
            } while (r < 0 && errno == EINTR);
            if (r > 0 && (pfd.revents & POLLOUT)) continue;
        }
        return -1;
    }
}

static int fdpass_reconnect_one(int idx, int wait_forever) {
    if (g_fdpass_upstreams[idx].fd >= 0) close(g_fdpass_upstreams[idx].fd);
    g_fdpass_upstreams[idx].fd = -1;

    for (int tries = 0; wait_forever || tries < 20; ++tries) {
        int fd = connect_unix_fdpass(g_fdpass_upstreams[idx].path);
        if (fd >= 0) {
            g_fdpass_upstreams[idx].fd = fd;
            return 0;
        }
        sleep_ms(wait_forever ? 25 : 2);
    }
    return -1;
}

static void fdpass_connect_all(void) {
    for (int i = 0; i < g_upstream_count; ++i) {
        strcpy(g_fdpass_upstreams[i].path, g_upstreams[i].path);
        g_fdpass_upstreams[i].fd = -1;
        (void)fdpass_reconnect_one(i, 1);
    }
}

static int fdpass_handoff(int idx, int client_fd) {
    if (g_fdpass_upstreams[idx].fd < 0 && fdpass_reconnect_one(idx, 0) != 0) return -1;
    if (send_fd(g_fdpass_upstreams[idx].fd, client_fd) == 0) return 0;
    if (fdpass_reconnect_one(idx, 0) != 0) return -1;
    return send_fd(g_fdpass_upstreams[idx].fd, client_fd);
}

static int fdpass_handoff_with_retry(int first, int client_fd) {
    for (int round = 0; round < 8; ++round) {
        for (int offset = 0; offset < g_upstream_count; ++offset) {
            int idx = (first + offset + round) % g_upstream_count;
            if (fdpass_handoff(idx, client_fd) == 0) return 0;
        }
        sleep_ms(1);
    }
    return -1;
}

static int run_fdpass(void) {
    parse_upstreams("/run/rinha/api1.sock,/run/rinha/api2.sock");
    fdpass_connect_all();

    int port = env_int("PORT", DEFAULT_PORT);
    int backlog = env_int("BACKLOG", DEFAULT_BACKLOG);
    int server_fd = listen_tcp(port, backlog);
    if (server_fd < 0) {
        perror("listen_tcp");
        return 1;
    }

    struct pollfd pfd;
    pfd.fd = server_fd;
    pfd.events = POLLIN;
    pfd.revents = 0;

    for (;;) {
        int r = poll(&pfd, 1, -1);
        if (r < 0) {
            if (errno == EINTR) continue;
            break;
        }
        if (!(pfd.revents & POLLIN)) continue;

        for (;;) {
            int client_fd = accept4(server_fd, NULL, NULL, SOCK_NONBLOCK | SOCK_CLOEXEC);
            if (client_fd < 0) {
                if (errno == EINTR) continue;
                if (errno == EAGAIN || errno == EWOULDBLOCK) break;
                break;
            }
            tune_tcp_socket(client_fd);
            int first = (int)(g_rr_next++ % (unsigned int)g_upstream_count);
            (void)fdpass_handoff_with_retry(first, client_fd);
            close(client_fd);
        }
    }

    close(server_fd);
    return 1;
}

/* ============================== proxy mode =============================== */

static void clear_ref(int fd) {
    if (fd >= 0 && fd < MAX_FDS) {
        g_fd_refs[fd].conn = NULL;
        g_fd_refs[fd].side = 0;
    }
}

static int set_ref(int fd, Conn *conn, int side) {
    if (fd < 0 || fd >= MAX_FDS) return -1;
    g_fd_refs[fd].conn = conn;
    g_fd_refs[fd].side = side;
    return 0;
}

static int proxy_connect_backend(int *connecting) {
    const char *path = g_upstreams[g_rr_next++ % (unsigned int)g_upstream_count].path;
    return connect_unix_nonblocking(path, connecting);
}

static void compact_buffer(char *buffer, size_t *off, size_t *len) {
    if (*off == 0 || *len == 0) return;
    memmove(buffer, buffer + *off, *len);
    *off = 0;
}

static int write_buffer(int fd, char *buffer, size_t *off, size_t *len) {
    while (*len > 0) {
        ssize_t sent = send(fd, buffer + *off, *len, MSG_NOSIGNAL);
        if (sent > 0) {
            *off += (size_t)sent;
            *len -= (size_t)sent;
            if (*len == 0) *off = 0;
            continue;
        }
        if (sent < 0 && errno == EINTR) continue;
        if (sent < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) return 0;
        return -1;
    }
    return 0;
}

static int read_into_buffer(int fd, char *buffer, size_t *off, size_t *len) {
    compact_buffer(buffer, off, len);
    while (*len < BUFFER_SIZE) {
        ssize_t got = recv(fd, buffer + *len, BUFFER_SIZE - *len, 0);
        if (got > 0) {
            *len += (size_t)got;
            continue;
        }
        if (got == 0) return -1;
        if (errno == EINTR) continue;
        if (errno == EAGAIN || errno == EWOULDBLOCK) return 0;
        return -1;
    }
    return 0;
}

static int update_events_for_fd(int fd) {
    if (fd < 0 || fd >= MAX_FDS) return -1;
    FdRef ref = g_fd_refs[fd];
    Conn *conn = ref.conn;
    if (conn == NULL) return -1;

    uint32_t events = EPOLLERR | EPOLLHUP | EPOLLRDHUP;
    if (ref.side == 0) {
        if (conn->c2b_len < BUFFER_SIZE) events |= EPOLLIN;
        if (conn->b2c_len > 0) events |= EPOLLOUT;
    } else {
        if (conn->backend_connecting) {
            events |= EPOLLOUT;
        } else {
            if (conn->b2c_len < BUFFER_SIZE) events |= EPOLLIN;
            if (conn->c2b_len > 0) events |= EPOLLOUT;
        }
    }

    struct epoll_event ev;
    memset(&ev, 0, sizeof(ev));
    ev.events = events;
    ev.data.fd = fd;
    return epoll_ctl(g_epoll_fd, EPOLL_CTL_MOD, fd, &ev);
}

static int add_fd(int fd, Conn *conn, int side, uint32_t events) {
    if (set_ref(fd, conn, side) < 0) return -1;
    struct epoll_event ev;
    memset(&ev, 0, sizeof(ev));
    ev.events = events | EPOLLERR | EPOLLHUP | EPOLLRDHUP;
    ev.data.fd = fd;
    if (epoll_ctl(g_epoll_fd, EPOLL_CTL_ADD, fd, &ev) < 0) {
        clear_ref(fd);
        return -1;
    }
    return 0;
}

static void close_conn(Conn *conn) {
    if (conn == NULL) return;
    if (conn->client_fd >= 0) {
        epoll_ctl(g_epoll_fd, EPOLL_CTL_DEL, conn->client_fd, NULL);
        clear_ref(conn->client_fd);
        close(conn->client_fd);
        conn->client_fd = -1;
    }
    if (conn->backend_fd >= 0) {
        epoll_ctl(g_epoll_fd, EPOLL_CTL_DEL, conn->backend_fd, NULL);
        clear_ref(conn->backend_fd);
        close(conn->backend_fd);
        conn->backend_fd = -1;
    }
    free(conn);
}

static int finish_backend_connect(Conn *conn) {
    int err = 0;
    socklen_t len = sizeof(err);
    if (getsockopt(conn->backend_fd, SOL_SOCKET, SO_ERROR, &err, &len) < 0) return -1;
    if (err != 0) return -1;
    conn->backend_connecting = 0;
    return 0;
}

static void accept_clients(int listen_fd) {
    for (;;) {
        int client_fd = accept4(listen_fd, NULL, NULL, SOCK_NONBLOCK | SOCK_CLOEXEC);
        if (client_fd < 0) {
            if (errno == EINTR) continue;
            if (errno == EAGAIN || errno == EWOULDBLOCK) return;
            return;
        }
        tune_tcp_socket(client_fd);

        int connecting = 0;
        int backend_fd = proxy_connect_backend(&connecting);
        if (backend_fd < 0) {
            close(client_fd);
            continue;
        }

        Conn *conn = (Conn *)calloc(1, sizeof(Conn));
        if (conn == NULL) {
            close(client_fd);
            close(backend_fd);
            continue;
        }
        conn->client_fd = client_fd;
        conn->backend_fd = backend_fd;
        conn->backend_connecting = connecting;

        if (add_fd(client_fd, conn, 0, EPOLLIN) < 0 ||
            add_fd(backend_fd, conn, 1, connecting ? EPOLLOUT : EPOLLIN) < 0) {
            close_conn(conn);
        }
    }
}

static void handle_fd(int fd, uint32_t events) {
    if (fd < 0 || fd >= MAX_FDS) return;
    FdRef ref = g_fd_refs[fd];
    Conn *conn = ref.conn;
    if (conn == NULL) return;

    if (events & (EPOLLERR | EPOLLHUP | EPOLLRDHUP)) {
        close_conn(conn);
        return;
    }

    if (ref.side == 1 && conn->backend_connecting && (events & EPOLLOUT)) {
        if (finish_backend_connect(conn) < 0) {
            close_conn(conn);
            return;
        }
    }

    if (events & EPOLLOUT) {
        int rc = ref.side == 0
            ? write_buffer(fd, conn->b2c, &conn->b2c_off, &conn->b2c_len)
            : write_buffer(fd, conn->c2b, &conn->c2b_off, &conn->c2b_len);
        if (rc < 0) {
            close_conn(conn);
            return;
        }
    }

    if (events & EPOLLIN) {
        int rc = ref.side == 0
            ? read_into_buffer(fd, conn->c2b, &conn->c2b_off, &conn->c2b_len)
            : read_into_buffer(fd, conn->b2c, &conn->b2c_off, &conn->b2c_len);
        if (rc < 0) {
            close_conn(conn);
            return;
        }
    }

    (void)update_events_for_fd(conn->client_fd);
    (void)update_events_for_fd(conn->backend_fd);
}

static int run_proxy(void) {
    parse_upstreams("/sockets/api1.sock,/sockets/api2.sock");

    int port = env_int("PORT", DEFAULT_PORT);
    int backlog = env_int("BACKLOG", DEFAULT_BACKLOG);
    int listen_fd = listen_tcp(port, backlog);
    if (listen_fd < 0) {
        perror("listen_tcp");
        return 1;
    }

    g_epoll_fd = epoll_create1(EPOLL_CLOEXEC);
    if (g_epoll_fd < 0) {
        perror("epoll_create1");
        close(listen_fd);
        return 1;
    }

    struct epoll_event ev;
    memset(&ev, 0, sizeof(ev));
    ev.events = EPOLLIN | EPOLLERR | EPOLLHUP;
    ev.data.fd = listen_fd;
    if (epoll_ctl(g_epoll_fd, EPOLL_CTL_ADD, listen_fd, &ev) < 0) {
        perror("epoll_ctl listen");
        close(g_epoll_fd);
        close(listen_fd);
        return 1;
    }

    struct epoll_event events[MAX_EVENTS];
    for (;;) {
        int n = epoll_wait(g_epoll_fd, events, MAX_EVENTS, -1);
        if (n < 0) {
            if (errno == EINTR) continue;
            perror("epoll_wait");
            return 1;
        }
        for (int i = 0; i < n; ++i) {
            int fd = events[i].data.fd;
            if (fd == listen_fd) {
                accept_clients(listen_fd);
            } else {
                handle_fd(fd, events[i].events);
            }
        }
    }
}

int main(void) {
    signal(SIGPIPE, SIG_IGN);
    set_limits();

    const char *mode = env_or("LB_MODE", env_or("MODE", "proxy"));
    if (streq_ci(mode, "fdpass") || streq_ci(mode, "fd-pass") || streq_ci(mode, "fd") || streq_ci(mode, "scm_rights")) {
        return run_fdpass();
    }
    if (streq_ci(mode, "proxy") || streq_ci(mode, "uds-proxy") || streq_ci(mode, "unix-proxy")) {
        return run_proxy();
    }

    fprintf(stderr, "unknown LB_MODE=%s; expected proxy or fdpass\n", mode);
    return 2;
}
