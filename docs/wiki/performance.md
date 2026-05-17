# Performance Notes

The ASM LB is promoted because it should reduce transport overhead without changing the backend contract.

## Promotion gates

1. zero correctness regressions and zero unexpected HTTP errors;
2. equal or lower p99 latency across downstream stacks;
3. stable behavior across repeated workflow runs;
4. no hidden socket-contract changes in compose files.

## What to watch

- `LB_MODE=proxy` should not parse payloads or add per-request logs.
- `LB_MODE=fdpass` should close the LB-owned accepted FD after handoff.
- `LB_FDPASS_SOCKET_TYPE` must match the backend control socket.
- GitHub-hosted runners are noisy, so one lucky p99 should not decide a promotion.

## Tag discipline

`latest` and release tags are ASM. Benchmark runs that need repeatability should pin `asm-ci-<sha>` or a release tag instead of relying on a moving pointer.
