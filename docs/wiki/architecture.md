# Architecture

The repository builds the promoted ASM load balancer from one source tree.

| Implementation | Build target | Image role | Purpose |
| --- | --- | --- | --- |
| ASM | `make all` or `make asm` | `latest`, release tags, `asm-ci-<sha>` | Promoted default path for Rinha4 stacks. |

The binary exposes two external runtime shapes.

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

Use this for raw HTTP backends such as the .NET implementation. The ASM proxy path accepts TCP clients, connects to one configured Unix stream upstream, forwards the request/response bytes, and closes the client after the exchange.

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

The ASM implementation accepts client sockets in blocking mode for fdpass so simple backend `read()` paths do not immediately see `EAGAIN`. Proxy mode keeps nonblocking sockets where forwarding loops need them.

## Design constraints

The default ASM LB is intentionally narrow:

- two upstream workers, matching the Rinha4 topology;
- no fraud payload parsing;
- no request-level logging;
- fixed minimal syscall path;
- environment parsing only for the contract knobs needed by the stacks.
