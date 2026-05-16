# Architecture

The C baseline currently supports two runtime shapes.

## Proxy mode

```text
k6 / judge
    |
    v
rinha4-lb-yolo-mode :9999
    |  epoll TCP <-> Unix stream proxy
    +-- unix:/sockets/api1.sock -> raw HTTP API
    +-- unix:/sockets/api2.sock -> raw HTTP API
```

Use this for raw HTTP backends such as the .NET implementation.

## FD-passing mode

```text
k6 / judge
    |
    v
rinha4-lb-yolo-mode :9999
    |  SCM_RIGHTS fd handoff over SOCK_SEQPACKET
    +-- unix:/run/rinha/api1.sock -> API receives accepted client fd
    +-- unix:/run/rinha/api2.sock -> API receives accepted client fd
```

Use this for APIs that are built around inherited accepted sockets, such as the C stack and the assembly stack lane.

The assembly variant should preserve the same externally visible contract before any attempt to tune it further.
