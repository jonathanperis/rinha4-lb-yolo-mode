# Getting Started

## Build and test locally

```sh
make clean test
```

The test target builds the LB and runs both modes against local dummy Unix-socket backends.

## Use the published image

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

For fd-passing stacks, switch `LB_MODE` to `fdpass` and point `UPSTREAMS` at the Unix control socket paths exposed by the API workers.
