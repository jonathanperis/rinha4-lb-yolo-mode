.intel_syntax noprefix
.global _start

.equ SYS_READ, 0
.equ SYS_WRITE, 1
.equ SYS_CLOSE, 3
.equ SYS_NANOSLEEP, 35
.equ SYS_SOCKET, 41
.equ SYS_CONNECT, 42
.equ SYS_SENDMSG, 46
.equ SYS_BIND, 49
.equ SYS_LISTEN, 50
.equ SYS_SETSOCKOPT, 54
.equ SYS_EXIT, 60
.equ SYS_ACCEPT4, 288

.equ AF_UNIX, 1
.equ AF_INET, 2
.equ SOCK_STREAM, 1
.equ SOCK_SEQPACKET, 5
.equ SOCK_NONBLOCK, 0x800
.equ SOCK_CLOEXEC, 0x80000
.equ SOL_SOCKET, 1
.equ SO_REUSEADDR, 2
.equ IPPROTO_TCP, 6
.equ TCP_NODELAY, 1
.equ SCM_RIGHTS, 1
.equ MSG_NOSIGNAL, 0x4000
.equ DEFAULT_PORT, 9999
.equ DEFAULT_BACKLOG, 65535
.equ RLIMIT_NOFILE, 7
.equ EINTR_NEG, -4
.equ EAGAIN_NEG, -11

.section .text
_start:
    mov dword ptr [rip + port_value], DEFAULT_PORT
    mov dword ptr [rip + backlog_value], DEFAULT_BACKLOG
    call parse_env

    cmp dword ptr [rip + mode_bad], 0
    jne unsupported_mode
    cmp dword ptr [rip + config_bad], 0
    jne invalid_config

    call set_nofile_limit

    cmp dword ptr [rip + proxy_mode], 0
    jne setup_listener

    lea rdi, [rip + api1_addr]
    call connect_forever
    mov qword ptr [rip + upstream1_fd], rax
    lea rdi, [rip + api2_addr]
    call connect_forever
    mov qword ptr [rip + upstream2_fd], rax

setup_listener:
    mov rax, SYS_SOCKET
    mov rdi, AF_INET
    mov rsi, SOCK_STREAM | SOCK_CLOEXEC
    xor rdx, rdx
    syscall
    test rax, rax
    js fatal
    mov r12, rax

    mov dword ptr [rip + optval], 1
    mov rax, SYS_SETSOCKOPT
    mov rdi, r12
    mov rsi, SOL_SOCKET
    mov rdx, SO_REUSEADDR
    lea r10, [rip + optval]
    mov r8, 4
    syscall

    mov rax, SYS_SETSOCKOPT
    mov rdi, r12
    mov rsi, IPPROTO_TCP
    mov rdx, TCP_NODELAY
    lea r10, [rip + optval]
    mov r8, 4
    syscall

    mov word ptr [rip + sockaddr_in], AF_INET
    mov ax, word ptr [rip + port_value]
    rol ax, 8
    mov word ptr [rip + sockaddr_in + 2], ax
    mov dword ptr [rip + sockaddr_in + 4], 0
    mov qword ptr [rip + sockaddr_in + 8], 0

    mov rax, SYS_BIND
    mov rdi, r12
    lea rsi, [rip + sockaddr_in]
    mov rdx, 16
    syscall
    test rax, rax
    js fatal

    mov rax, SYS_LISTEN
    mov rdi, r12
    mov esi, dword ptr [rip + backlog_value]
    syscall
    test rax, rax
    js fatal

accept_loop:
    mov rax, SYS_ACCEPT4
    mov rdi, r12
    xor rsi, rsi
    xor rdx, rdx
    mov r10, SOCK_CLOEXEC
    cmp dword ptr [rip + proxy_mode], 0
    je 1f
    mov r10, SOCK_NONBLOCK | SOCK_CLOEXEC
1:
    syscall
    test rax, rax
    js accept_loop
    mov r13, rax

    mov rax, SYS_SETSOCKOPT
    mov rdi, r13
    mov rsi, IPPROTO_TCP
    mov rdx, TCP_NODELAY
    lea r10, [rip + optval]
    mov r8, 4
    syscall

    mov rax, qword ptr [rip + rr_next]
    xor rax, 1
    mov qword ptr [rip + rr_next], rax
    test rax, rax
    jz first_upstream1

first_upstream2:
    cmp dword ptr [rip + proxy_mode], 0
    jne proxy_first_upstream2
    mov rdi, 2
    mov rsi, r13
    call handoff
    test rax, rax
    jz close_client
    mov rdi, 1
    mov rsi, r13
    call handoff
    jmp close_client

first_upstream1:
    cmp dword ptr [rip + proxy_mode], 0
    jne proxy_first_upstream1
    mov rdi, 1
    mov rsi, r13
    call handoff
    test rax, rax
    jz close_client
    mov rdi, 2
    mov rsi, r13
    call handoff

close_client:
    mov rax, SYS_CLOSE
    mov rdi, r13
    syscall
    jmp accept_loop

proxy_first_upstream2:
    mov rdi, 2
    mov rsi, r13
    call proxy_handoff
    test rax, rax
    jz close_client
    mov rdi, 1
    mov rsi, r13
    call proxy_handoff
    jmp close_client

proxy_first_upstream1:
    mov rdi, 1
    mov rsi, r13
    call proxy_handoff
    test rax, rax
    jz close_client
    mov rdi, 2
    mov rsi, r13
    call proxy_handoff
    jmp close_client

unsupported_mode:
    mov rax, SYS_WRITE
    mov rdi, 2
    lea rsi, [rip + unsupported_msg]
    mov rdx, 57
    syscall
    mov rax, SYS_EXIT
    mov rdi, 2
    syscall

invalid_config:
    mov rax, SYS_WRITE
    mov rdi, 2
    lea rsi, [rip + invalid_config_msg]
    mov rdx, 29
    syscall
    mov rax, SYS_EXIT
    mov rdi, 1
    syscall

fatal:
    mov rax, SYS_EXIT
    mov rdi, 1
    syscall

set_nofile_limit:
    # Ignore errors.  struct rlimit { rlim_cur, rlim_max } = {65535,65535}
    mov qword ptr [rip + rlimit_buf], 65535
    mov qword ptr [rip + rlimit_buf + 8], 65535
    mov rax, 160              # setrlimit
    mov rdi, RLIMIT_NOFILE
    lea rsi, [rip + rlimit_buf]
    syscall
    ret

# rdi = upstream number (1 or 2), rsi = client fd. Returns 0 on success, -1 on failure.
handoff:
    push rdi
    push rsi
    cmp rdi, 1
    je 1f
    mov rdi, qword ptr [rip + upstream2_fd]
    jmp 2f
1:
    mov rdi, qword ptr [rip + upstream1_fd]
2:
    mov rsi, qword ptr [rsp]
    call send_fd
    test rax, rax
    jz 9f

    # reconnect selected upstream once and retry
    cmp qword ptr [rsp + 8], 1
    je 4f
    mov rax, SYS_CLOSE
    mov rdi, qword ptr [rip + upstream2_fd]
    syscall
    lea rdi, [rip + api2_addr]
    call connect_once
    test rax, rax
    js 8f
    mov qword ptr [rip + upstream2_fd], rax
    mov rdi, rax
    jmp 5f
4:
    mov rax, SYS_CLOSE
    mov rdi, qword ptr [rip + upstream1_fd]
    syscall
    lea rdi, [rip + api1_addr]
    call connect_once
    test rax, rax
    js 8f
    mov qword ptr [rip + upstream1_fd], rax
    mov rdi, rax
5:
    mov rsi, qword ptr [rsp]
    call send_fd
    test rax, rax
    jz 9f
8:
    mov rax, -1
    add rsp, 16
    ret
9:
    xor rax, rax
    add rsp, 16
    ret


# rdi = upstream number (1 or 2), rsi = client fd. Returns 0 on success, -1 on failure.
# Simple single-connection proxy for SOCK_STREAM Unix upstreams. It forwards the
# currently available HTTP request bytes, then relays response bytes until the
# upstream closes or remains idle briefly. This is intentionally small and keeps
# the ASM target dependency-free; the C target remains the high-throughput proxy.
proxy_handoff:
    push rdi
    push rsi
    cmp rdi, 1
    je 1f
    lea rdi, [rip + api2_addr]
    jmp 2f
1:
    lea rdi, [rip + api1_addr]
2:
    call connect_once
    test rax, rax
    js proxy_fail
    mov r14, rax                 # upstream fd

    # Wait briefly for first client bytes, then read until HTTP headers finish
    # (\r\n\r\n) or the client stays idle for a short grace period. Split TCP
    # requests commonly arrive with an EAGAIN gap between header fragments.
    mov dword ptr [rip + header_window], 0
    mov dword ptr [rip + header_complete], 0
    mov r15d, 1000
proxy_read_client:
    mov rax, SYS_READ
    mov rdi, qword ptr [rsp]     # client fd
    lea rsi, [rip + proxy_buf]
    mov rdx, 16384
    syscall
    test rax, rax
    jg proxy_write_request
    cmp rax, 0
    je proxy_done_close_upstream
    cmp rax, EINTR_NEG
    je proxy_read_client
    cmp rax, EAGAIN_NEG
    jne proxy_done_close_upstream
    dec r15d
    jz proxy_response_loop_init
    lea rdi, [rip + send_retry_sleep]
    xor rsi, rsi
    mov rax, SYS_NANOSLEEP
    syscall
    jmp proxy_read_client

proxy_write_request:
    mov rbx, rax                 # preserve read length across header scan
    lea rdi, [rip + proxy_buf]
    mov rsi, rbx
    call scan_http_headers
    mov rdi, r14
    lea rsi, [rip + proxy_buf]
    mov rdx, rbx
    call write_all
    test rax, rax
    jnz proxy_done_close_upstream
    cmp dword ptr [rip + header_complete], 0
    jne proxy_response_loop_init
    mov r15d, 100                # tolerate delayed split request fragments (~100ms)
    jmp proxy_read_client

proxy_response_loop_init:
    mov r15d, 2000
proxy_response_loop:
    mov rax, SYS_READ
    mov rdi, r14
    lea rsi, [rip + proxy_buf]
    mov rdx, 16384
    syscall
    test rax, rax
    jg proxy_write_response
    cmp rax, 0
    je proxy_success_close_upstream
    cmp rax, EINTR_NEG
    je proxy_response_loop
    cmp rax, EAGAIN_NEG
    jne proxy_done_close_upstream
    dec r15d
    jz proxy_success_close_upstream
    lea rdi, [rip + send_retry_sleep]
    xor rsi, rsi
    mov rax, SYS_NANOSLEEP
    syscall
    jmp proxy_response_loop

proxy_write_response:
    mov rdi, qword ptr [rsp]     # client fd
    lea rsi, [rip + proxy_buf]
    mov rdx, rax
    call write_all
    test rax, rax
    jnz proxy_done_close_upstream
    mov r15d, 2000
    jmp proxy_response_loop

proxy_success_close_upstream:
    mov rax, SYS_CLOSE
    mov rdi, r14
    syscall
    xor rax, rax
    add rsp, 16
    ret

proxy_done_close_upstream:
    mov rax, SYS_CLOSE
    mov rdi, r14
    syscall
proxy_fail:
    mov rax, -1
    add rsp, 16
    ret

# rdi=buf, rsi=len. Tracks a rolling 4-byte window and sets header_complete
# after seeing the HTTP header delimiter \r\n\r\n, including across reads.
scan_http_headers:
    mov eax, dword ptr [rip + header_window]
    test rsi, rsi
    jz 9f
1:
    movzx edx, byte ptr [rdi]
    shl eax, 8
    or eax, edx
    cmp eax, 0x0d0a0d0a
    jne 2f
    mov dword ptr [rip + header_complete], 1
2:
    inc rdi
    dec rsi
    jnz 1b
9:
    mov dword ptr [rip + header_window], eax
    ret

# rdi=fd, rsi=buf, rdx=len. Returns 0 on success, -1 on failure.
write_all:
    push rbx
    push r12
    push r13
    mov rbx, rdi
    mov r12, rsi
    mov r13, rdx
1:
    test r13, r13
    jz 9f
    mov rax, SYS_WRITE
    mov rdi, rbx
    mov rsi, r12
    mov rdx, r13
    syscall
    test rax, rax
    jg 2f
    cmp rax, EINTR_NEG
    je 1b
    cmp rax, EAGAIN_NEG
    jne 8f
    lea rdi, [rip + send_retry_sleep]
    xor rsi, rsi
    mov rax, SYS_NANOSLEEP
    syscall
    jmp 1b
2:
    add r12, rax
    sub r13, rax
    jmp 1b
8:
    mov rax, -1
    pop r13
    pop r12
    pop rbx
    ret
9:
    xor rax, rax
    pop r13
    pop r12
    pop rbx
    ret

# rdi = sockaddr_un*. Returns fd or negative errno.
connect_forever:
    push rdi
1:
    mov rdi, qword ptr [rsp]
    call connect_once
    test rax, rax
    jns 2f
    lea rdi, [rip + retry_sleep]
    xor rsi, rsi
    mov rax, SYS_NANOSLEEP
    syscall
    jmp 1b
2:
    add rsp, 8
    ret

# rdi = sockaddr_un*. Returns fd or negative errno.
connect_once:
    push rdi
    mov rax, SYS_SOCKET
    mov rdi, AF_UNIX
    mov rsi, SOCK_SEQPACKET | SOCK_NONBLOCK | SOCK_CLOEXEC
    cmp dword ptr [rip + proxy_mode], 0
    jne 0f
    cmp dword ptr [rip + fdpass_stream_mode], 0
    je 1f
0:
    mov rsi, SOCK_STREAM | SOCK_NONBLOCK | SOCK_CLOEXEC
1:
    xor rdx, rdx
    syscall
    test rax, rax
    js 9f
    mov rbx, rax
    mov rax, SYS_CONNECT
    mov rdi, rbx
    mov rsi, qword ptr [rsp]
    mov rdx, 110
    syscall
    test rax, rax
    js 8f
    mov rax, rbx
    add rsp, 8
    ret
8:
    mov rax, SYS_CLOSE
    mov rdi, rbx
    syscall
    mov rax, -1
9:
    add rsp, 8
    ret

# rdi = unix control socket, rsi = client fd. Returns 0 on success, -1 on failure.
send_fd:
    push rdi
    mov qword ptr [rip + iov_base], OFFSET FLAT:send_byte
    mov qword ptr [rip + iov_len], 1
    mov qword ptr [rip + msg_name], 0
    mov qword ptr [rip + msg_namelen], 0
    mov qword ptr [rip + msg_iov], OFFSET FLAT:iov_base
    mov qword ptr [rip + msg_iovlen], 1
    mov qword ptr [rip + msg_control], OFFSET FLAT:cmsg_buf
    mov qword ptr [rip + msg_controllen], 24
    mov qword ptr [rip + msg_flags], 0
    mov qword ptr [rip + cmsg_buf], 20
    mov dword ptr [rip + cmsg_buf + 8], SOL_SOCKET
    mov dword ptr [rip + cmsg_buf + 12], SCM_RIGHTS
    mov dword ptr [rip + cmsg_buf + 16], esi
    mov dword ptr [rip + cmsg_buf + 20], 0

    mov r8d, 16
send_fd_try:
    mov rdi, qword ptr [rsp]
    mov rax, SYS_SENDMSG
    lea rsi, [rip + msg_name]
    mov rdx, MSG_NOSIGNAL
    syscall
    cmp rax, 1
    je 1f
    cmp rax, EINTR_NEG
    je 2f
    cmp rax, EAGAIN_NEG
    je 3f
    mov rax, -1
    add rsp, 8
    ret
2:
    dec r8d
    jnz send_fd_try
    mov rax, -1
    add rsp, 8
    ret
3:
    dec r8d
    jz 4f
    push r8
    lea rdi, [rip + send_retry_sleep]
    xor rsi, rsi
    mov rax, SYS_NANOSLEEP
    syscall
    pop r8
    jmp send_fd_try
4:
    mov rax, -1
    add rsp, 8
    ret
1:
    xor rax, rax
    add rsp, 8
    ret

parse_env:
    mov rbx, qword ptr [rsp + 8]
    lea r14, [rsp + 24]
    lea r14, [r14 + rbx*8]         # envp = rsp_at_start + 8*(argc+2)
1:
    mov rdi, qword ptr [r14]
    test rdi, rdi
    jz 9f

    lea rsi, [rip + env_lb_mode]
    call match_prefix
    test rax, rax
    jz 2f
    mov rdi, rax
    cmp byte ptr [rdi], 0
    je 8f
    push rdi
    call mode_is_fdpass
    test rax, rax
    pop rdi
    jnz 8f
    lea rsi, [rip + mode_proxy_str]
    call streq
    test rax, rax
    jz 7f
    mov dword ptr [rip + proxy_mode], 1
    jmp 8f
7:
    mov dword ptr [rip + mode_bad], 1
    jmp 8f

2:
    mov rdi, qword ptr [r14]
    lea rsi, [rip + env_port]
    call match_prefix
    test rax, rax
    jz 3f
    mov rdi, rax
    mov esi, DEFAULT_PORT
    call parse_dec
    mov dword ptr [rip + port_value], eax
    jmp 8f

3:
    mov rdi, qword ptr [r14]
    lea rsi, [rip + env_backlog]
    call match_prefix
    test rax, rax
    jz 4f
    mov rdi, rax
    mov esi, DEFAULT_BACKLOG
    call parse_dec
    mov dword ptr [rip + backlog_value], eax
    jmp 8f

4:
    mov rdi, qword ptr [r14]
    lea rsi, [rip + env_upstreams]
    call match_prefix
    test rax, rax
    jz 5f
    mov rdi, rax
    call parse_upstreams
    jmp 8f

5:
    mov rdi, qword ptr [r14]
    lea rsi, [rip + env_fdpass_socket_type]
    call match_prefix
    test rax, rax
    jz 8f
    mov rdi, rax
    lea rsi, [rip + socktype_stream]
    call streq
    test rax, rax
    jz 8f
    mov dword ptr [rip + fdpass_stream_mode], 1

8:
    add r14, 8
    jmp 1b
9:
    ret

# rdi=str, rsi=prefix. Returns pointer just after prefix, or 0.
match_prefix:
    push rdi
1:
    mov al, byte ptr [rsi]
    test al, al
    jz 2f
    cmp byte ptr [rdi], al
    jne 3f
    inc rdi
    inc rsi
    jmp 1b
2:
    mov rax, rdi
    add rsp, 8
    ret
3:
    xor rax, rax
    add rsp, 8
    ret

mode_is_fdpass:
    push rdi
    lea rsi, [rip + mode_fdpass]
    call streq
    test rax, rax
    jnz 9f
    mov rdi, qword ptr [rsp]
    lea rsi, [rip + mode_fd]
    call streq
    test rax, rax
    jnz 9f
    mov rdi, qword ptr [rsp]
    lea rsi, [rip + mode_fd_dash]
    call streq
    test rax, rax
    jnz 9f
    mov rdi, qword ptr [rsp]
    lea rsi, [rip + mode_scm]
    call streq
9:
    add rsp, 8
    ret

# rdi=a, rsi=b. Returns 1 iff equal.
streq:
    push rdi
1:
    mov al, byte ptr [rdi]
    mov dl, byte ptr [rsi]
    cmp al, dl
    jne 2f
    test al, al
    jz 3f
    inc rdi
    inc rsi
    jmp 1b
2:
    xor rax, rax
    add rsp, 8
    ret
3:
    mov rax, 1
    add rsp, 8
    ret

# rdi=decimal string, esi=fallback. Returns eax.
parse_dec:
    mov eax, esi
    xor edx, edx
    xor ecx, ecx
1:
    mov bl, byte ptr [rdi]
    test bl, bl
    jz 2f
    cmp bl, '0'
    jb 3f
    cmp bl, '9'
    ja 3f
    cmp edx, 6553
    ja 3f
    jne 4f
    cmp bl, '5'
    ja 3f
4:
    imul edx, edx, 10
    movzx ebx, bl
    sub ebx, '0'
    add edx, ebx
    mov ecx, 1
    inc rdi
    jmp 1b
2:
    test ecx, ecx
    jz 3f
    test edx, edx
    jz 3f
    mov eax, edx
3:
    ret

parse_upstreams:
    push rdi
    lea rdi, [rip + api1_addr + 2]
    call zero_path
    lea rdi, [rip + api2_addr + 2]
    call zero_path
    pop rsi                  # source
    lea rdi, [rip + api1_addr + 2]
    xor edx, edx             # first length
1:
    mov al, byte ptr [rsi]
    test al, al
    jz 8f
    cmp al, ','
    je 2f
    cmp edx, 107
    jae 8f
    mov byte ptr [rdi], al
    inc rdi
    inc rsi
    inc edx
    jmp 1b
2:
    test edx, edx
    jz 8f
    mov byte ptr [rdi], 0
    inc rsi
    lea rdi, [rip + api2_addr + 2]
    xor edx, edx             # second length
3:
    mov al, byte ptr [rsi]
    test al, al
    jz 4f
    cmp al, ','
    je 8f
    cmp edx, 107
    jae 8f
    mov byte ptr [rdi], al
    inc rdi
    inc rsi
    inc edx
    jmp 3b
4:
    test edx, edx
    jz 8f
    mov byte ptr [rdi], 0
    ret
8:
    mov dword ptr [rip + config_bad], 1
    ret

zero_path:
    mov ecx, 108
    xor eax, eax
1:
    mov byte ptr [rdi], al
    inc rdi
    loop 1b
    ret

.section .rodata
retry_sleep:
    .quad 0
    .quad 25000000
send_retry_sleep:
    .quad 0
    .quad 1000000
unsupported_msg:
    .ascii "unsupported LB_MODE for asm lb; expected fdpass or proxy\n"
.equ unsupported_msg_len, . - unsupported_msg
invalid_config_msg:
    .ascii "invalid asm lb configuration\n"
.equ invalid_config_msg_len, . - invalid_config_msg

env_lb_mode: .asciz "LB_MODE="
env_port: .asciz "PORT="
env_backlog: .asciz "BACKLOG="
env_upstreams: .asciz "UPSTREAMS="
env_fdpass_socket_type: .asciz "LB_FDPASS_SOCKET_TYPE="
mode_fdpass: .asciz "fdpass"
mode_fd: .asciz "fd"
mode_fd_dash: .asciz "fd-pass"
mode_scm: .asciz "scm_rights"
mode_proxy_str: .asciz "proxy"
socktype_stream: .asciz "stream"
send_byte: .byte 1

.section .data
api1_addr:
    .word AF_UNIX
    .asciz "/run/rinha/api1.sock"
    .zero 108 - (. - api1_addr - 2)
api2_addr:
    .word AF_UNIX
    .asciz "/run/rinha/api2.sock"
    .zero 108 - (. - api2_addr - 2)

.section .bss
.align 16
sockaddr_in: .skip 16
optval: .skip 4
port_value: .skip 4
backlog_value: .skip 4
mode_bad: .skip 4
config_bad: .skip 4
proxy_mode: .skip 4
fdpass_stream_mode: .skip 4
header_window: .skip 4
header_complete: .skip 4
upstream1_fd: .skip 8
upstream2_fd: .skip 8
rr_next: .skip 8
rlimit_buf: .skip 16
.align 8
iov_base: .skip 8
iov_len: .skip 8
msg_name: .skip 8
msg_namelen: .skip 8
msg_iov: .skip 8
msg_iovlen: .skip 8
msg_control: .skip 8
msg_controllen: .skip 8
msg_flags: .skip 8
cmsg_buf: .skip 32
proxy_buf: .skip 16384
