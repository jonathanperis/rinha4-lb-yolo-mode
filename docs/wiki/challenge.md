# Challenge

Rinha de Backend 2026 is scored by an official-like k6 workload against a constrained Docker Compose stack. The load balancer is in the hot path for every request, so transport overhead, connection churn, descriptor handling, and scheduler behavior matter.

For this repo, the question is narrow:

> Can the shared YOLO load balancer move from C to assembly and become the default LB for all Jonathan Peris Rinha4 implementations?

The answer must be based on comparison evidence, not a single noisy CI run. The comparison lane keeps the official-like benchmark matrix visible and separates candidate results from experiments.
