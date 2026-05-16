# Contracts

## Environment

| Variable | Default | Description |
| --- | ---: | --- |
| `LB_MODE` | `proxy` | `proxy` or `fdpass`. Aliases: `uds-proxy`, `fd`, `fd-pass`. |
| `PORT` | `9999` | TCP listen port. |
| `UPSTREAMS` | mode-specific | Comma-separated Unix socket paths. |
| `BACKLOG` | `65535` | TCP listen backlog. |

## Proxy-mode contract

- Listen on TCP `PORT`.
- Connect each accepted client to one configured Unix stream upstream.
- Forward bytes without parsing fraud payloads.
- Keep TCP descriptors nonblocking and avoid per-request logging in the candidate path.

## FD-passing contract

- Maintain persistent `SOCK_SEQPACKET` Unix control sockets to API workers.
- Accept TCP clients on `PORT`.
- Mark accepted client FDs nonblocking before handoff.
- Send FDs with `SCM_RIGHTS` and close the LB copy after handoff.
- Do not inspect or mutate request payloads.
