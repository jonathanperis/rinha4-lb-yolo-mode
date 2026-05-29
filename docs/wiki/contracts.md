# Contracts

## Environment

| Variable | Default | Description |
| --- | ---: | --- |
| `LB_MODE` | `proxy` | `proxy` or `fdpass`; promoted ASM aliases are `fd`, `fd-pass`, and `scm_rights`. |
| `PORT` | `9999` | TCP listen port. Invalid numeric values fall back to `9999` in the integration-tested paths. |
| `UPSTREAMS` | mode-specific | Comma-separated Unix socket paths. Proxy default is `/sockets/api1.sock,/sockets/api2.sock`; fdpass default is `/run/rinha/api1.sock,/run/rinha/api2.sock`. |
| `BACKLOG` | `65535` | TCP listen backlog. Invalid numeric values fall back to `65535` in the integration-tested paths. |
| `LB_FDPASS_SOCKET_TYPE` | `seqpacket` | FD-passing control socket type. Use `seqpacket` or `stream` to match the backend control socket. |

Compatibility notes:

- The promoted ASM binary reads `LB_MODE`, `PORT`, `BACKLOG`, `UPSTREAMS`, and `LB_FDPASS_SOCKET_TYPE` directly from its environment.
- The ASM binary is static/no-libc and ignores unrelated environment variables injected by Docker or GitHub Actions.
- The C baseline accepts `MODE` as a fallback when `LB_MODE` is unset, and also accepts `uds-proxy`/`unix-proxy` for proxy mode.
- The ASM binary intentionally requires exactly two non-empty upstream paths shorter than the Linux `sun_path` limit. The C baseline supports up to 16 upstreams.
- ASM `PORT` and `BACKLOG` parsing accepts positive decimal values up to `65535`; invalid values fall back to `9999` and `65535` respectively.
- Published containers target linux/amd64 and run as the unprivileged `rinha` user.

## Image contract

| Tag family | Implementation | Use |
| --- | --- | --- |
| `latest` | ASM | Default stack image. |
| `vX.Y.Z` | ASM | Release image for a promoted main commit. |
| `asm-ci-<sha>` | ASM | Immutable ASM comparison and rollout image. |
| `sha-<short-sha>` | ASM | Docker metadata short-SHA alias for the same ASM manifest as `asm-ci-<sha>`. |
| `c-ci-<sha>` | C | Immutable C baseline image published by the build workflow. |
| `c-latest` | C | Moving C baseline pointer; avoid for repeatable benchmarks. |

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
| Raw HTTP backend | `proxy` | Unix stream HTTP upstreams. |
| FD-passing backend | `fdpass` | Usually `LB_FDPASS_SOCKET_TYPE=seqpacket`. |
| Assembly backend fdpass lane | `fdpass` | Usually `LB_FDPASS_SOCKET_TYPE=stream`. Verify the active compose before benchmarking. |

Correctness comes before p99. If any participant reports false positives, false negatives, HTTP errors, or readiness failures, reject that comparison result before reading latency.
