# rinha4-lb-yolo-mode

Standalone YOLO-mode load balancer for Jonathan Peris' Rinha de Backend 2026 entries.

The default implementation is now the x86-64 assembly LB. The original C implementation stays in the repository as the readable baseline and as the image used by the comparison lane when we need C-vs-ASM evidence.

## Published images

```text
ghcr.io/jonathanperis/rinha4-lb-yolo-mode:latest        # default ASM LB
ghcr.io/jonathanperis/rinha4-lb-yolo-mode:vX.Y.Z        # release tag, default ASM LB
ghcr.io/jonathanperis/rinha4-lb-yolo-mode:asm-ci-<sha>  # commit-specific ASM LB
ghcr.io/jonathanperis/rinha4-lb-yolo-mode:c-ci-<sha>    # commit-specific C baseline
ghcr.io/jonathanperis/rinha4-lb-yolo-mode:c-latest      # latest C baseline
```

`latest` is the promoted ASM binary. Use `c-ci-<sha>` or `c-latest` only when running an explicit baseline comparison.

## Runtime modes

Both implementations expose the same external contract:

- `LB_MODE=proxy`: TCP acceptor that connects each client to a Unix stream HTTP backend. Use this with raw HTTP APIs such as `rinha4-back-end-dotnet`.
- `LB_MODE=fdpass`: TCP acceptor that sends accepted client FDs to API workers with `SCM_RIGHTS`. Use this with entries that process inherited sockets, such as `rinha4-back-end-c` and the assembly backend lane.

The ASM implementation is intentionally narrow for the Rinha4 topology: two upstream workers, payload-agnostic forwarding, no request parsing, no access logs, and only the knobs needed by the benchmark stacks.

## Configuration

| Variable | Default | Description |
| --- | ---: | --- |
| `LB_MODE` | `proxy` | `proxy` or `fdpass`. Aliases: `uds-proxy`, `fd`, `fd-pass`. |
| `PORT` | `9999` | TCP listen port. |
| `UPSTREAMS` | mode-specific | Comma-separated Unix socket paths. Proxy default is `/sockets/api1.sock,/sockets/api2.sock`; fdpass default is `/run/rinha/api1.sock,/run/rinha/api2.sock`. |
| `BACKLOG` | `65535` | TCP listen backlog. |
| `LB_FDPASS_SOCKET_TYPE` | `seqpacket` | ASM fdpass control socket type. Use `seqpacket` for the C stack and `stream` for .NET or standalone assembly fdpass contracts that expect stream control sockets. |

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
      LB_FDPASS_SOCKET_TYPE: seqpacket
      PORT: "9999"
      UPSTREAMS: /run/rinha/api1.sock,/run/rinha/api2.sock
    ports:
      - "9999:9999"
    volumes:
      - sockets:/run/rinha
```

## Assembly fd-passing compose note

If the backend control socket is `SOCK_STREAM`, keep `LB_MODE=fdpass` and switch the control type:

```yaml
environment:
  LB_MODE: fdpass
  LB_FDPASS_SOCKET_TYPE: stream
  UPSTREAMS: /run/rinha/api1.sock,/run/rinha/api2.sock
```

## Local build/test

```bash
make clean test           # builds and tests C plus ASM
make clean all            # builds the default ASM binary
make clean all LB_IMPL=c  # builds the C baseline binary
make asm                  # builds build/rinha4-lb-yolo-mode-asm
make c                    # builds build/rinha4-lb-yolo-mode-c
```

The integration tests run proxy and fdpass smoke checks against local dummy Unix-socket backends. The ASM test also validates bad mode handling, upstream validation, decimal parsing, and stream-vs-seqpacket fdpass selection.

## Docs and reports

GitHub Pages lives under `docs/` and follows the same structure used by the Rinha4 API repositories:

- `/` home page for the promoted ASM LB and the C baseline comparison lane
- `/docs/` markdown-backed wiki from `docs/wiki/*.md`
- `/reports/` latest comparison summary copied from `comparison-results/latest.json`

Build locally with Bun:

```bash
cd docs
bun install --frozen-lockfile
NODE_ENV=production bun run build
```
