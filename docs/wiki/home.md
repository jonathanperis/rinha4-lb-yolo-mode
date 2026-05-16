# rinha4-lb-yolo-mode

Standalone YOLO-mode load balancer for Jonathan Peris' Rinha de Backend 2026 entries.

This repository is the transport workbench shared by three Rinha4 stacks:

- [`rinha4-back-end-dotnet`](https://github.com/jonathanperis/rinha4-back-end-dotnet): .NET 10 NativeAOT backend using raw HTTP over Unix sockets behind proxy mode.
- [`rinha4-back-end-c`](https://github.com/jonathanperis/rinha4-back-end-c): pure C backend receiving accepted client FDs through fd-passing mode.
- [`rinha4-yolo-mode`](https://github.com/jonathanperis/rinha4-yolo-mode): pure x86-64 assembly backend, used as the assembly lane for proving an assembly LB replacement.

The current published image is the C baseline:

```text
ghcr.io/jonathanperis/rinha4-lb-yolo-mode:latest
```

The active experiment is to promote an assembly LB variant only if it matches or improves the C baseline across the .NET, C, and assembly stacks under official-like comparison runs.
