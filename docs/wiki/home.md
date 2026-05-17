# Home

The promoted default is the x86-64 assembly load balancer. It is the shared YOLO-mode transport layer for Jonathan Peris' Rinha de Backend 2026 entries.

## Downstream stacks

- [`rinha4-back-end-dotnet`](https://github.com/jonathanperis/rinha4-back-end-dotnet): .NET 10 NativeAOT backend using raw HTTP over Unix sockets behind proxy mode.
- fd-passing backend lanes: APIs that receive accepted client FDs through Unix control sockets.
- [`rinha4-yolo-mode`](https://github.com/jonathanperis/rinha4-yolo-mode): pure x86-64 assembly backend, used as the assembly lane for proving the shared ASM LB.

## Image contract

```text
ghcr.io/jonathanperis/rinha4-lb-yolo-mode:latest        # promoted ASM LB
ghcr.io/jonathanperis/rinha4-lb-yolo-mode:vX.Y.Z        # release tag, promoted ASM LB
ghcr.io/jonathanperis/rinha4-lb-yolo-mode:asm-ci-<sha>  # commit-specific ASM LB
```

The comparison lane still matters. Future default changes should keep runs clean, repeated, and separated from official runner evidence.
