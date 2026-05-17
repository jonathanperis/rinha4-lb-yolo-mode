# Comparison Lane

The comparison workflow benchmarks the promoted ASM LB against the C baseline across the Rinha4 implementation families.

| Participant | Purpose |
| --- | --- |
| `dotnet-c-lb` | .NET API behind the C baseline LB. |
| `dotnet-asm-lb` | .NET API behind the promoted ASM LB. |
| `c-c-lb` | C API behind the C baseline LB. |
| `c-asm-lb` | C API behind the promoted ASM LB. |
| `yolo-current-lb` | YOLO/assembly API behind its currently pinned stack LB. |
| `yolo-standalone-asm-lb` | Assembly backend behind the standalone/shared ASM LB; this lane may be experimental while socket contracts are being tuned. |

The main workflow's matrix writes participant artifacts and then summarizes them into `comparison-results/latest.json`. The Pages workflow copies that file into `docs/public/comparison/latest.json` when it exists so the site can render the latest table.

## Branch shape

The `comparison` branch should stay a lean benchmark harness. It normally tracks only:

- `.github/workflows/benchmark.yml`;
- `LICENSE`;
- `competitor-compose/**`;
- `comparison-results/**`.

Do not merge `main` wholesale into `comparison` just to refresh the harness. Copy or cherry-pick only the workflow, compose files, and archived results that belong to the benchmark lane.

## Evidence rules

- Pin image tags for every participant.
- Use `asm-ci-<sha>` for ASM lanes and `c-ci-<sha>` for C baseline lanes; prefer matching SHAs when the comparison is meant to isolate implementation differences.
- Keep `latest` and `c-latest` out of comparisons unless the test is explicitly about the current moving pointer.
- Record whether the fdpass socket contract is `seqpacket` or `stream`.
- Keep CI-vs-CI and official-vs-official conclusions separate.
- Reject correctness failures before evaluating p99.
