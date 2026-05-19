FROM alpine:3.20 AS build

# Build the promoted ASM image by default. CI also builds the C baseline by
# overriding LB_IMPL=c, which keeps C-vs-ASM comparisons reproducible.
ARG LB_IMPL=asm
RUN apk add --no-cache build-base
WORKDIR /src
COPY . .
RUN make clean all LB_IMPL="${LB_IMPL}" CFLAGS_ARCH="-march=haswell -mtune=haswell -mavx2 -mfma -flto -fomit-frame-pointer -fno-plt -fno-semantic-interposition -fno-trapping-math" \
    && strip build/rinha4-lb-yolo-mode

FROM alpine:3.20

RUN adduser -D -H rinha
COPY --from=build /src/build/rinha4-lb-yolo-mode /rinha4-lb-yolo-mode
USER rinha
EXPOSE 9999
ENTRYPOINT ["/rinha4-lb-yolo-mode"]
