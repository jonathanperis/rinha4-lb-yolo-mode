FROM alpine:3.20 AS build

RUN apk add --no-cache clang lld make musl-dev
WORKDIR /src
COPY . .
RUN make clean all CC=clang CFLAGS_ARCH="-march=haswell -flto -fuse-ld=lld -fomit-frame-pointer" \
    && strip build/rinha4-lb-yolo-mode

FROM alpine:3.20

RUN adduser -D -H rinha
COPY --from=build /src/build/rinha4-lb-yolo-mode /rinha4-lb-yolo-mode
USER rinha
EXPOSE 9999
ENTRYPOINT ["/rinha4-lb-yolo-mode"]
