# Design Direction

## Scene

An engineer is checking a Rinha4 transport rollout late at night on a desktop monitor. The page is a control bench for confirming that the promoted assembly load balancer remains safe across the Rinha4 stacks. Dark mode fits the scene, but the interface must be calm enough for docs reading.

## Visual Language

- Base: near-black graphite.
- Panels: subtle blue-black glass with thin borders.
- Accent: electric cyan and violet for ASM/runtime signals.
- Muted text: blue-gray.
- Warning/accent: copper only for caution states, not for old implementation history.
- Cyan: proxy/fdpass transport lines.

## UX Goals

- The first screen should say ASM is default.
- Runtime contracts should be visible without scrolling through source-level history.
- Benchmark/report pages should prioritize correctness before p99.
- Docs pages should feel like an operator runbook, not a marketing splash.
