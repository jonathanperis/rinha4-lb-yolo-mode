# Getting Started

## Build and test locally

```sh
make clean test
```

The test target builds the load balancer and runs local integration checks against dummy Unix-socket backends.

```sh
make clean all            # default ASM binary: build/rinha4-lb-yolo-mode
make asm                  # build/rinha4-lb-yolo-mode-asm
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
```

Docker access is required for image builds. The repository integration tests do not require Docker.
