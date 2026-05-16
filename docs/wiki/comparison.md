# Comparison Lane

The comparison workflow benchmarks six participants:

| Participant | Purpose |
| --- | --- |
| `dotnet-c-lb` | .NET API behind current C YOLO LB |
| `dotnet-asm-lb` | .NET API behind assembly LB candidate |
| `c-c-lb` | C API behind current C YOLO LB |
| `c-asm-lb` | C API behind assembly LB candidate |
| `yolo-current-lb` | Assembly backend with current shared LB baseline |
| `yolo-standalone-asm-lb` | Assembly backend with standalone assembly LB candidate |

The workflow writes `comparison-results/latest.json`; the Pages workflow copies that file into `docs/public/comparison/latest.json` so the site can render the latest table.

Keep CI-vs-CI and official-vs-official lanes separate. CI comparisons are regression signals; official runner results are the source of truth for final promotion.
