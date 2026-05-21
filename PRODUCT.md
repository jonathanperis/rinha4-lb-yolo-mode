# Product

## Product Purpose

`rinha4-lb-yolo-mode` is the public documentation, release, and benchmark evidence surface for Jonathan Peris' shared Rinha de Backend 2026 load balancer. The default load balancer is the x86-64 assembly implementation used by the Rinha4 stacks.

## Audiences

- Rinha reviewers or competitors checking topology, image contracts, and benchmark evidence.
- Future maintainers who need to understand proxy mode, fd-passing mode, image tags, and promotion gates without reading the full source first.
- Jonathan's downstream stack repositories that consume the shared LB image.

## Product Principles

- Default is explicit: `latest` and release tags mean ASM.
- Transport clarity: make proxy mode, fd-passing mode, and fdpass socket type understandable at a glance.
- Evidence-first: correctness gates outrank latency conclusions.
- Source-backed copy: public docs should describe the current promoted path without dragging internal implementation history into user-facing pages.

## Primary Surfaces

- README: repository contract and quick usage.
- GitHub Pages home: visual overview of the promoted ASM LB.
- Docs wiki: architecture, contracts, getting started, and comparison workflow notes.
- Reports: latest archived benchmark summary when available.
