# Getting Started

## Build and test locally

```sh
make clean test
make docs-drift
```

The test target builds the C and ASM load balancers, runs `docs-drift`, then runs local integration checks against dummy Unix-socket backends. `docs-drift` is the quick audit for README/wiki drift: it checks image tags, runtime knobs, workflow inputs, and sidebar coverage against source files.

```sh
make clean all            # default ASM binary: build/rinha4-lb-yolo-mode
make asm                  # build/rinha4-lb-yolo-mode-asm
make c                    # build/rinha4-lb-yolo-mode-c
```

## Use the promoted ASM image

```yaml
services:
  lb:
    image: ghcr.io/jonathanperis/rinha4-lb-yolo-mode:latest
    platform: linux/amd64
    environment:
      LB_MODE: proxy
      PORT: "9999"
      UPSTREAMS: /sockets/api1.sock,/sockets/api2.sock
    ports:
      - "9999:9999"
```

`latest` is ASM. For a pinned rollout, prefer `asm-ci-<sha>` or a release tag.

## Use the C baseline image

```yaml
services:
  lb:
    image: ghcr.io/jonathanperis/rinha4-lb-yolo-mode:c-ci-<sha>
    platform: linux/amd64
    environment:
      LB_MODE: proxy
      PORT: "9999"
      UPSTREAMS: /sockets/api1.sock,/sockets/api2.sock
    ports:
      - "9999:9999"
```

Use the C image only for comparison and fallback experiments. `c-latest` exists, but repeatable benchmark runs should pin `c-ci-<sha>`.

## Use fdpass mode

```yaml
services:
  lb:
    image: ghcr.io/jonathanperis/rinha4-lb-yolo-mode:latest
    platform: linux/amd64
    environment:
      LB_MODE: fdpass
      LB_FDPASS_SOCKET_TYPE: seqpacket
      PORT: "9999"
      UPSTREAMS: /run/rinha/api1.sock,/run/rinha/api2.sock
    ports:
      - "9999:9999"
```

For stream fdpass backends, switch only the socket contract:

```yaml
environment:
  LB_MODE: fdpass
  LB_FDPASS_SOCKET_TYPE: stream
  UPSTREAMS: /run/rinha/api1.sock,/run/rinha/api2.sock
```

## Build the image locally

```sh
docker build --build-arg LB_IMPL=asm -t rinha4-lb-yolo-mode:asm .
docker build --build-arg LB_IMPL=c   -t rinha4-lb-yolo-mode:c .
```

Docker access is required for image builds. The repository integration tests do not require Docker.

The Dockerfile publishes linux/amd64 images, builds the ASM implementation by default, strips the binary, exposes port `9999`, and runs the runtime stage as the unprivileged `rinha` user. Override `LB_IMPL=c` only when building the C comparison image.
