# Performance Notes

The ASM LB is promoted because it should reduce transport overhead without changing the backend contract. The C implementation remains published so each claim can be checked against a pinned same-commit baseline.

## Promotion gates

1. zero correctness regressions and zero unexpected HTTP errors;
2. equal or lower p99 latency across downstream stacks;
3. stable behavior across repeated workflow runs;
4. no hidden socket-contract changes in compose files;
5. same-lane image tags: compare `asm-ci-<sha>` against `c-ci-<sha>` for the same commit whenever possible.

## What to watch

- `LB_MODE=proxy` should not parse payloads or add per-request logs.
- `LB_MODE=fdpass` should close the LB-owned accepted FD after handoff.
- `LB_FDPASS_SOCKET_TYPE` must match the backend control socket.
- GitHub-hosted runners are noisy, so one lucky p99 should not decide a promotion.
- `latest`, `c-latest`, and release tags are moving or semver pointers; pin immutable tags for evidence.

## Tag discipline

`latest` and release tags are ASM. Benchmark runs that need repeatability should pin `asm-ci-<sha>` for the promoted implementation and `c-ci-<sha>` for the C baseline instead of relying on a moving pointer.
