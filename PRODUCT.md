# PRODUCT

## Register
brand

## Product Purpose
`rinha4-lb-yolo-mode` is the public documentation, release, and benchmark evidence surface for Jonathan Peris' shared Rinha de Backend 2026 load balancer. The default load balancer is now the x86-64 assembly implementation, with the original C implementation retained as a readable baseline and comparison image for .NET, C, and assembly Rinha4 stacks.

## Users
- Jonathan and agents rolling the promoted ASM LB through Rinha4 repos.
- Rinha reviewers or competitors checking topology, image contracts, and benchmark evidence.
- Future maintainers who need to understand proxy mode, fd-passing mode, C baseline tags, and promotion gates without reading the full source first.

## Brand Voice
Precise, mechanical, and evidence-first. The site should feel like an instrument bench: measured, sharp, and operational. It should not read like a generic SaaS landing page or a decorative terminal theme.

## Strategic Principles
- Default is explicit: `latest` and release tags mean ASM after this promotion.
- Baseline remains visible: C tags exist for repeatable C-vs-ASM comparison, not as hidden legacy.
- Transport clarity: make proxy mode, fd-passing mode, and fdpass socket type understandable at a glance.
- Correctness before p99: false positives, false negatives, HTTP errors, or readiness failures reject a run before latency analysis.
- CI is signal, not truth: separate CI comparisons from official runner evidence.

## Anti-References
- CRT scanlines over long-form text.
- Clipped navigation and giant headline overflow.
- Fake metrics or decorative benchmark numbers.
- Low contrast code blocks.
- Repeated identical feature cards.
