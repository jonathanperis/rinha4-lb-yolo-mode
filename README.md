# rinha4-lb-yolo-mode

Standalone YOLO-mode load balancer for Jonathan Peris' Rinha de Backend 2026 entries.

The default container image is the x86-64 assembly LB. The repository still builds and publishes a C baseline so comparison runs can measure the promoted ASM path against the previous implementation.

## Published images

```text
ghcr.io/jonathanperis/rinha4-lb-yolo-mode:latest        # promoted ASM LB
ghcr.io/jonathanperis/rinha4-lb-yolo-mode:vX.Y.Z        # release tag, promoted ASM LB
ghcr.io/jonathanperis/rinha4-lb-yolo-mode:asm-ci-<sha>  # commit-specific ASM LB
ghcr.io/jonathanperis/rinha4-lb-yolo-mode:c-ci-<sha>    # commit-specific C baseline LB
ghcr.io/jonathanperis/rinha4-lb-yolo-mode:c-latest      # moving C baseline pointer
```

Use `asm-ci-<sha>` or a release tag when a benchmark or downstream rollout needs an immutable ASM image. Use `c-ci-<sha>` only for C-vs-ASM comparison lanes; it is not the promoted default.

## Runtime modes

Both implementations expose the same two external contracts:

- `LB_MODE=proxy`: TCP acceptor that connects each client to one Unix stream HTTP backend. Use this with raw HTTP APIs such as `rinha4-back-end-dotnet`.
- `LB_MODE=fdpass`: TCP acceptor that sends accepted client FDs to API workers with `SCM_RIGHTS`. Use this with entries that process inherited sockets.

The promoted ASM binary accepts `proxy`, `fdpass`, `fd`, `fd-pass`, and `scm_rights`. The C baseline also accepts `MODE` as a fallback variable and the extra proxy aliases `uds-proxy` and `unix-proxy`.

The ASM implementation is intentionally narrow for the Rinha4 topology: exactly two upstream workers, payload-agnostic forwarding, no request parsing, no access logs, and only the knobs needed by the benchmark stacks. The C baseline keeps a more general epoll implementation with up to 16 upstream paths for comparison and fallback experiments.

## Configuration

| Variable | Default | Description |
| --- | ---: | --- |
| `LB_MODE` | `proxy` | `proxy` or `fdpass`; promoted ASM aliases are `fd`, `fd-pass`, and `scm_rights`. |
| `PORT` | `9999` | TCP listen port. Invalid numeric values fall back to `9999` in the integration-tested paths. |
| `UPSTREAMS` | mode-specific | Comma-separated Unix socket paths. Proxy default is `/sockets/api1.sock,/sockets/api2.sock`; fdpass default is `/run/rinha/api1.sock,/run/rinha/api2.sock`. |
| `BACKLOG` | `65535` | TCP listen backlog. Invalid numeric values fall back to `65535` in the integration-tested paths. |
| `LB_FDPASS_SOCKET_TYPE` | `seqpacket` | FD-passing control socket type. Use `seqpacket` or `stream` to match the backend control socket. |

Runtime guardrails worth keeping visible in compose reviews:

- published images are linux/amd64 only and the Docker runtime drops to the unprivileged `rinha` user;
- the ASM binary is static/no-libc, reads only the documented environment knobs, and ignores unrelated container metadata;
- ASM decimal parsing accepts positive values up to `65535` for `PORT`/`BACKLOG`; invalid or out-of-range values fall back to the defaults;
- ASM `UPSTREAMS` validation requires exactly two non-empty Unix socket paths shorter than the Linux `sun_path` limit; the C baseline is broader and accepts up to 16 paths;
- use `LB_FDPASS_SOCKET_TYPE=stream` only when the backend control sockets are `SOCK_STREAM`; leave the default `seqpacket` for seqpacket control sockets.

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
make clean test           # builds C + ASM and runs integration tests
make docs-drift           # checks README/wiki facts against source/workflows
make clean all            # builds the default ASM binary at build/rinha4-lb-yolo-mode
make asm                  # builds build/rinha4-lb-yolo-mode-asm
make c                    # builds build/rinha4-lb-yolo-mode-c
```

The test target runs `docs-drift`, then proxy and fdpass smoke checks against local dummy Unix-socket backends. The ASM test also validates bad mode handling, upstream validation, decimal parsing fallback, and stream-vs-seqpacket fdpass selection.

## Container builds

```bash
docker build --build-arg LB_IMPL=asm -t rinha4-lb-yolo-mode:asm .
docker build --build-arg LB_IMPL=c   -t rinha4-lb-yolo-mode:c .
```

Docker access is required for image builds. The repository integration tests do not require Docker.

## Docs and reports

GitHub Pages lives under `docs/` and follows the same structure used by the Rinha4 API repositories:

- `/` home page for the promoted ASM LB;
- `/docs/` markdown-backed wiki from `docs/wiki/*.md`;
- `/reports/` latest comparison summary copied from `comparison-results/latest.json` when that artifact exists.

Build locally with Bun:

```bash
cd docs
bun install --frozen-lockfile
NODE_ENV=production bun run build
```
