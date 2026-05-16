# Performance

Performance conclusions must be drawn from repeated official-like comparisons because GitHub-hosted runners are noisy.

The decision rule for adopting the assembly LB should require:

1. zero correctness regressions and zero unexpected HTTP errors;
2. equal or lower p99 latency versus the C LB for .NET, C, and assembly stacks;
3. stable behavior across repeated workflow runs;
4. no contract drift that forces API-specific hacks into the shared LB.

The LB itself should stay payload-agnostic. It wins only by reducing accept, epoll, Unix-socket, fd-passing, and copy overhead.
