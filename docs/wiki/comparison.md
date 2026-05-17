# Comparison Lane

The comparison workflow benchmarks the promoted ASM LB against the retained C baseline across the three Rinha4 implementation families.

| Participant | Purpose |
| --- | --- |
| `dotnet-c-lb` | .NET API behind pinned C YOLO LB baseline. |
| `dotnet-asm-lb` | .NET API behind promoted ASM LB. |
| `c-c-lb` | C API behind pinned C YOLO LB baseline. |
| `c-asm-lb` | C API behind promoted ASM LB. |
| `yolo-c-lb` or `yolo-current-lb` | Assembly backend behind shared C baseline, when the lane needs it. |
| `yolo-standalone-asm-lb` | Assembly backend behind the standalone or shared ASM LB, depending on the active experiment. |

The workflow writes `comparison-results/latest.json`; the Pages workflow copies that file into `docs/public/comparison/latest.json` so the site can render the latest table.

## Branch shape

The `comparison` branch should stay a lean benchmark harness. It normally tracks only:

- `.github/workflows/benchmark.yml`;
- `LICENSE`;
- `competitor-compose/**`;
- `comparison-results/**`.

Do not merge `main` wholesale into `comparison` just to refresh the harness. Copy or cherry-pick only the workflow, compose files, and archived results that belong to the benchmark lane.

## Evidence rules

- Pin image tags for every participant.
- Keep `latest` out of comparisons unless the test is explicitly about the current default pointer.
- Record whether the fdpass socket contract is `seqpacket` or `stream`.
- Keep CI-vs-CI and official-vs-official conclusions separate.
- Reject correctness failures before evaluating p99.
