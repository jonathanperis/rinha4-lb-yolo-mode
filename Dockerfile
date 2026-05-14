FROM alpine:3.20 AS build

RUN apk add --no-cache build-base
WORKDIR /src
COPY . .
RUN make clean all CFLAGS_ARCH="-march=x86-64-v3 -flto -fomit-frame-pointer" \
    && strip build/rinha4-lb-yolo-mode

FROM alpine:3.20

RUN adduser -D -H rinha
COPY --from=build /src/build/rinha4-lb-yolo-mode /rinha4-lb-yolo-mode
USER rinha
EXPOSE 9999
ENTRYPOINT ["/rinha4-lb-yolo-mode"]
