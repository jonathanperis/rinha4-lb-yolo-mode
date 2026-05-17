# Performance

Performance conclusions must be drawn from repeated official-like comparisons because GitHub-hosted runners are noisy.

The current default is ASM, but the decision rule does not relax:

1. zero correctness regressions and zero unexpected HTTP errors;
2. equal or lower p99 latency versus the C LB for .NET, C, and assembly stacks;
3. stable behavior across repeated workflow runs;
4. no contract drift that forces API-specific hacks into the shared LB.

The LB itself should stay payload-agnostic. It wins only by reducing accept, Unix-socket, fd-passing, and byte-forwarding overhead.

## Reading results

Use this order:

1. Verify every participant reached a clean score gate: no false positives, no false negatives, no HTTP errors.
2. Confirm the image tags and socket contracts for that run.
3. Compare p99 only inside the same lane: CI-vs-CI or official-vs-official.
4. Repeat close calls before changing defaults in downstream repos.

## Default image rule

`latest` and release tags are ASM. Baseline comparisons should pin a C image explicitly with `c-ci-<sha>` or `c-latest`; never assume `latest` means C after this promotion.
