# Comparison Lane

The comparison workflow benchmarks the promoted ASM LB across the Rinha4 implementation families.

| Participant | Purpose |
| --- | --- |
| `dotnet-asm-lb` | .NET API behind the promoted ASM LB. |
| `fdpass-asm-lb` | FD-passing API behind the promoted ASM LB. |
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
