# Challenge

Rinha de Backend 2026 is scored by an official-like k6 workload against a constrained Docker Compose stack. The load balancer is in the hot path for every request, so transport overhead, connection churn, descriptor handling, and scheduler behavior matter.

For this repo, the promotion question has moved from planning to defaulting:

> The shared YOLO load balancer now defaults to the x86-64 assembly implementation. Can it stay the default across .NET, C, and assembly stacks without correctness or p99 regressions?

That answer still depends on evidence, not a single noisy CI run. The repo keeps both implementations so every future change can compare:

- default ASM image versus pinned C baseline;
- proxy mode for raw Unix-socket HTTP APIs;
- fdpass mode for accepted-socket APIs;
- CI-vs-CI regression runs separately from official runner results.

A default promotion is only useful if the surface stays honest about what was tested, which image was used, which socket contract was selected, and whether the run was official or official-like CI.
