# Challenge

Rinha de Backend rewards correctness first and latency second. A faster LB is only useful if it preserves the official contract under repeated, official-like runs.

> The shared YOLO load balancer now defaults to the x86-64 assembly implementation. Can it stay the default across the downstream stacks without correctness or p99 regressions?

The comparison harness exists to answer that by testing:

- the promoted ASM image under pinned tags;
- proxy mode for raw Unix-socket HTTP APIs;
- fdpass mode for accepted-socket APIs;
- repeated runs to smooth noisy GitHub-hosted runners;
- official-vs-official results separately from CI-vs-CI runs.

Correctness failures close the result immediately. p99 only matters after false positives, false negatives, HTTP errors, and readiness checks are clean.
