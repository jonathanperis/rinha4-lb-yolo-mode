# Home

The promoted default is the x86-64 assembly load balancer. It is the shared YOLO-mode transport layer for Jonathan Peris' Rinha de Backend 2026 entries, with a C baseline kept in the same repo for controlled C-vs-ASM comparisons.

## Downstream stacks

- [`rinha4-back-end-dotnet`](https://github.com/jonathanperis/rinha4-back-end-dotnet): .NET 10 NativeAOT backend using raw HTTP over Unix sockets behind proxy mode.
- [`rinha4-back-end-c`](https://github.com/jonathanperis/rinha4-back-end-c): C fraud-scoring backend, usually benchmarked behind either the C baseline LB or the promoted ASM LB.
- [`rinha4-yolo-mode`](https://github.com/jonathanperis/rinha4-yolo-mode): pure x86-64 assembly backend, used as the assembly lane for proving the shared ASM LB.
- FD-passing backend lanes: APIs that receive accepted client FDs through Unix control sockets.

## Image contract

```text
ghcr.io/jonathanperis/rinha4-lb-yolo-mode:latest        # promoted ASM LB
ghcr.io/jonathanperis/rinha4-lb-yolo-mode:vX.Y.Z        # release tag, promoted ASM LB
ghcr.io/jonathanperis/rinha4-lb-yolo-mode:asm-ci-<sha>  # commit-specific ASM LB
ghcr.io/jonathanperis/rinha4-lb-yolo-mode:c-ci-<sha>    # commit-specific C baseline LB
ghcr.io/jonathanperis/rinha4-lb-yolo-mode:c-latest      # moving C baseline pointer
```

`latest` and release tags mean ASM. Use immutable `asm-ci-<sha>` or `c-ci-<sha>` tags for comparison runs so CI-vs-CI evidence does not mix moving pointers.

The comparison lane still matters. Future default changes should keep C-vs-ASM runs clean, repeated, and separated from official runner evidence.
