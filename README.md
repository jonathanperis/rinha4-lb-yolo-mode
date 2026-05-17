# rinha4-lb-yolo-mode

Standalone YOLO-mode load balancer for Jonathan Peris' Rinha de Backend 2026 entries.

The default implementation is the x86-64 assembly LB. It is the promoted shared transport layer for the Rinha4 stacks and exposes both proxy and fd-passing runtime contracts.

## Published images

```text
ghcr.io/jonathanperis/rinha4-lb-yolo-mode:latest        # default ASM LB
ghcr.io/jonathanperis/rinha4-lb-yolo-mode:vX.Y.Z        # release tag, default ASM LB
ghcr.io/jonathanperis/rinha4-lb-yolo-mode:asm-ci-<sha>  # commit-specific ASM LB
```

`latest` is the promoted ASM binary. Use `asm-ci-<sha>` or a release tag when a benchmark or downstream rollout needs an immutable image.

## Runtime modes

The ASM binary exposes two external contracts:

- `LB_MODE=proxy`: TCP acceptor that connects each client to a Unix stream HTTP backend. Use this with raw HTTP APIs such as `rinha4-back-end-dotnet`.
- `LB_MODE=fdpass`: TCP acceptor that sends accepted client FDs to API workers with `SCM_RIGHTS`. Use this with entries that process inherited sockets.

The ASM implementation is intentionally narrow for the Rinha4 topology: two upstream workers, payload-agnostic forwarding, no request parsing, no access logs, and only the knobs needed by the benchmark stacks.

## Configuration

| Variable | Default | Description |
| --- | ---: | --- |
| `LB_MODE` | `proxy` | `proxy` or `fdpass`. Aliases: `uds-proxy`, `fd`, `fd-pass`. |
| `PORT` | `9999` | TCP listen port. |
| `UPSTREAMS` | mode-specific | Comma-separated Unix socket paths. Proxy default is `/sockets/api1.sock,/sockets/api2.sock`; fdpass default is `/run/rinha/api1.sock,/run/rinha/api2.sock`. |
| `BACKLOG` | `65535` | TCP listen backlog. |
| `LB_FDPASS_SOCKET_TYPE` | `seqpacket` | ASM fdpass control socket type. Use `seqpacket` or `stream` to match the backend control socket. |

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

## FD-passing compose example

```yaml
services:
  lb:
    image: ghcr.io/jonathanperis/rinha4-lb-yolo-mode:latest
    platform: linux/amd64
    environment:
      LB_MODE: fdpass
      LB_FDPASS_SOCKET_TYPE: seqpacket
      PORT: "9999"
      UPSTREAMS: /run/rinha/api1.sock,/run/rinha/api2.sock
    ports:
      - "9999:9999"
    volumes:
      - sockets:/run/rinha
```

## Stream fd-passing compose note

If the backend control socket is `SOCK_STREAM`, keep `LB_MODE=fdpass` and switch the control type:

```yaml
environment:
  LB_MODE: fdpass
  LB_FDPASS_SOCKET_TYPE: stream
  UPSTREAMS: /run/rinha/api1.sock,/run/rinha/api2.sock
```

## Local build/test

```bash
make clean test           # builds and tests the load balancer
make clean all            # builds the default ASM binary
make asm                  # builds build/rinha4-lb-yolo-mode-asm
```

The integration tests run proxy and fdpass smoke checks against local dummy Unix-socket backends. The ASM test also validates bad mode handling, upstream validation, decimal parsing, and stream-vs-seqpacket fdpass selection.

## Docs and reports

GitHub Pages lives under `docs/` and follows the same structure used by the Rinha4 API repositories:

- `/` home page for the promoted ASM LB
- `/docs/` markdown-backed wiki from `docs/wiki/*.md`
- `/reports/` latest comparison summary copied from `comparison-results/latest.json`

Build locally with Bun:

```bash
cd docs
bun install --frozen-lockfile
NODE_ENV=production bun run build
```
