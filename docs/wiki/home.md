# rinha4-lb-yolo-mode

Standalone YOLO-mode load balancer for Jonathan Peris' Rinha de Backend 2026 entries.

The promoted default is now the x86-64 assembly load balancer. The original C implementation remains in-tree as the readable baseline, fallback target, and C-vs-ASM comparison image.

This repository is the transport workbench shared by three Rinha4 stacks:

- [`rinha4-back-end-dotnet`](https://github.com/jonathanperis/rinha4-back-end-dotnet): .NET 10 NativeAOT backend using raw HTTP over Unix sockets behind proxy mode.
- [`rinha4-back-end-c`](https://github.com/jonathanperis/rinha4-back-end-c): pure C backend receiving accepted client FDs through fd-passing mode.
- [`rinha4-yolo-mode`](https://github.com/jonathanperis/rinha4-yolo-mode): pure x86-64 assembly backend, used as the assembly lane for proving the shared ASM LB.

Current image roles:

```text
ghcr.io/jonathanperis/rinha4-lb-yolo-mode:latest        # promoted ASM LB
ghcr.io/jonathanperis/rinha4-lb-yolo-mode:asm-ci-<sha>  # commit-specific ASM LB
ghcr.io/jonathanperis/rinha4-lb-yolo-mode:c-ci-<sha>    # commit-specific C baseline
ghcr.io/jonathanperis/rinha4-lb-yolo-mode:c-latest      # latest C baseline
```

The comparison lane still matters. Promotion to default means `latest` now points at ASM, not that the C baseline evidence is discarded. Future default changes should keep C-vs-ASM runs clean, repeated, and separated from official runner evidence.
