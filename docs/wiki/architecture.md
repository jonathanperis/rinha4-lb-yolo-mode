# Architecture

The repository builds two load-balancer implementations from one source tree. The default runtime image is ASM; the C binary is retained as a baseline and troubleshooting fallback.

| Implementation | Build target | Published image role | Purpose |
| --- | --- | --- | --- |
| ASM | `make all` or `make asm` | `latest`, release tags, `asm-ci-<sha>`, `sha-<short-sha>` | Promoted default path for Rinha4 stacks. |
| C | `make c` or `docker build --build-arg LB_IMPL=c` | `c-ci-<sha>`, `c-latest` | Baseline for C-vs-ASM comparison lanes and fallback experiments. |

Both binaries expose the same two external runtime shapes.

## Proxy mode

```text
k6 / judge
    |
    v
rinha4-lb-yolo-mode :9999
    |  TCP acceptor to Unix stream proxy
    +-- unix:/sockets/api1.sock -> raw HTTP API
    +-- unix:/sockets/api2.sock -> raw HTTP API
```

Use this for raw HTTP backends such as the .NET implementation. The promoted ASM proxy path accepts TCP clients, connects to one configured Unix stream upstream, forwards request/response bytes without parsing the fraud payload, and closes the client after the exchange.

## FD-passing mode

```text
k6 / judge
    |
    v
rinha4-lb-yolo-mode :9999
    |  SCM_RIGHTS accepted-fd handoff
    +-- unix:/run/rinha/api1.sock -> API receives accepted client fd
    +-- unix:/run/rinha/api2.sock -> API receives accepted client fd
```

Use this for APIs built around inherited accepted sockets.

The fdpass control socket type is explicit:

- `LB_FDPASS_SOCKET_TYPE=seqpacket` for datagram-preserving control sockets;
- `LB_FDPASS_SOCKET_TYPE=stream` for stream control sockets.

The ASM implementation accepts client sockets in blocking mode for fdpass so simple backend `read()` paths do not immediately see `EAGAIN`. Proxy mode uses a compact blocking syscall loop in ASM; the C baseline uses epoll/nonblocking forwarding.

## Design constraints

The default ASM LB is intentionally narrow:

- exactly two upstream workers, matching the Rinha4 topology and enforced by the ASM validation path;
- no fraud payload parsing;
- no request-level logging;
- fixed minimal syscall path;
- environment parsing only for the contract knobs needed by the stacks.

The C baseline supports up to 16 upstream paths and broader mode aliases, but it is not the promoted image.
