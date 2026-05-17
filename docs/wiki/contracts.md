# Contracts

## Environment

| Variable | Default | Description |
| --- | ---: | --- |
| `LB_MODE` | `proxy` | `proxy` or `fdpass`. Aliases: `uds-proxy`, `fd`, `fd-pass`. |
| `PORT` | `9999` | TCP listen port. |
| `UPSTREAMS` | mode-specific | Comma-separated Unix socket paths. Proxy default is `/sockets/api1.sock,/sockets/api2.sock`; fdpass default is `/run/rinha/api1.sock,/run/rinha/api2.sock`. |
| `BACKLOG` | `65535` | TCP listen backlog. |
| `LB_FDPASS_SOCKET_TYPE` | `seqpacket` | ASM fdpass control socket type. Use `seqpacket` for the C stack and `stream` for stream fdpass contracts. |

## Image contract

| Tag family | Implementation | Use |
| --- | --- | --- |
| `latest` | ASM | Default stack image. |
| `vX.Y.Z` | ASM | Release image for a promoted main commit. |
| `asm-ci-<sha>` | ASM | Immutable comparison and rollout image. |
| `c-ci-<sha>` | C | Immutable C baseline for comparison. |
| `c-latest` | C | Convenience C baseline pointer. |

## Proxy-mode contract

- Listen on TCP `PORT`.
- Connect each accepted client to one configured Unix stream upstream.
- Forward bytes without parsing fraud payloads.
- Avoid per-request logging in the hot path.
- Keep the runtime compatible with raw HTTP backends.

## FD-passing contract

- Maintain persistent Unix control sockets to API workers.
- Accept TCP clients on `PORT`.
- Send accepted client FDs with `SCM_RIGHTS`.
- Close the LB copy after handoff.
- Do not inspect or mutate request payloads.
- Match the worker socket type with `LB_FDPASS_SOCKET_TYPE`.

## Stack-specific socket type

| Stack | Mode | Socket type |
| --- | --- | --- |
| `rinha4-back-end-dotnet` | `proxy` | Unix stream HTTP upstreams. |
| `rinha4-back-end-c` | `fdpass` | `LB_FDPASS_SOCKET_TYPE=seqpacket`. |
| Assembly backend fdpass lane | `fdpass` | Usually `LB_FDPASS_SOCKET_TYPE=stream`. Verify the active compose before benchmarking. |

Correctness comes before p99. If any participant reports false positives, false negatives, HTTP errors, or readiness failures, reject that comparison result before reading latency.
