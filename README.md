# rinha4-lb-yolo-mode

Standalone YOLO-mode load balancer for Jonathan Peris' Rinha de Backend 2026 entries.

This image packages the two low-level C load-balancer strategies that were proven in the C and .NET repositories:

- `LB_MODE=proxy`: epoll TCP-to-Unix-domain-socket stream proxy. Use this with raw HTTP backends that listen on Unix sockets, e.g. the .NET entry.
- `LB_MODE=fdpass`: TCP acceptor with persistent Unix control sockets and `SCM_RIGHTS` file-descriptor handoff. Use this with APIs that receive accepted client sockets from the LB, e.g. the C entry.

The published image is:

```text
ghcr.io/jonathanperis/rinha4-lb-yolo-mode:latest
```

Commit-specific CI images are also published as `ci-<sha>`.

## Configuration

| Variable | Default | Description |
|---|---:|---|
| `LB_MODE` | `proxy` | `proxy` or `fdpass`. Aliases: `uds-proxy`, `fd`, `fd-pass`. |
| `PORT` | `9999` | TCP listen port. |
| `UPSTREAMS` | mode-specific | Comma-separated Unix socket paths. Proxy default is `/sockets/api1.sock,/sockets/api2.sock`; fdpass default is `/run/rinha/api1.sock,/run/rinha/api2.sock`. |
| `BACKLOG` | `65535` | TCP listen backlog. |

## .NET/raw-UDS compose example

```yaml
services:
  lb:
    image: ghcr.io/jonathanperis/rinha4-lb-yolo-mode:latest
    platform: linux/amd64
    environment:
      LB_MODE: proxy
      PORT: "9999"
      UPSTREAMS: /sockets/api1.sock,/sockets/api2.sock
    ports:
      - "9999:9999"
    volumes:
      - sockets:/sockets
```

## C/fd-passing compose example

```yaml
services:
  lb:
    image: ghcr.io/jonathanperis/rinha4-lb-yolo-mode:latest
    platform: linux/amd64
    environment:
      LB_MODE: fdpass
      PORT: "9999"
      UPSTREAMS: /run/rinha/api1.sock,/run/rinha/api2.sock
    ports:
      - "9999:9999"
    volumes:
      - sockets:/run/rinha
```

## Local build/test

```bash
make clean test
```

The tests compile the binary and run both modes against local dummy Unix-socket backends.

## Hot paths

`proxy` mode keeps a generic `UPSTREAMS` fallback, but automatically takes a two-upstream fast path for the normal Rinha shape. That path uses the same round-robin shape as the embedded .NET C LB (`next++ & 1`) and avoids zeroing the 8 KiB connection buffers on accept.
