CC ?= cc
BUILD_DIR := build
TARGET := $(BUILD_DIR)/rinha4-lb-yolo-mode
C_TARGET := $(BUILD_DIR)/rinha4-lb-yolo-mode-c
ASM_TARGET := $(BUILD_DIR)/rinha4-lb-yolo-mode-asm
LB_IMPL ?= asm
CFLAGS_WARN := -Wall -Wextra -Wshadow -Werror
CFLAGS_ARCH ?=
ASMFLAGS_ARCH ?= -march=x86-64-v3
CFLAGS_COMMON := -std=c11 -O3 -DNDEBUG $(CFLAGS_ARCH) $(CFLAGS_WARN)
LDFLAGS_COMMON :=
ASMFLAGS_COMMON := -O3 -nostdlib -static -no-pie $(ASMFLAGS_ARCH)

.PHONY: all c asm clean test test-c test-asm

all: $(TARGET)

c: $(C_TARGET)

asm: $(ASM_TARGET)

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(C_TARGET): src/yolo_lb.c | $(BUILD_DIR)
	$(CC) $(CFLAGS_COMMON) $< -o $@ $(LDFLAGS_COMMON)

$(ASM_TARGET): src/yolo_lb_fdpass.S | $(BUILD_DIR)
	$(CC) $(ASMFLAGS_COMMON) $< -o $@

$(TARGET): $(if $(filter asm,$(LB_IMPL)),$(ASM_TARGET),$(C_TARGET)) | $(BUILD_DIR)
	cp $< $@

test: test-c test-asm

test-c: $(C_TARGET)
	python3 tests/integration_test.py $(C_TARGET)

test-asm: $(ASM_TARGET)
	LB_TEST_MODES=fdpass,proxy,invalid-lb-mode,bad-upstreams,parse-dec python3 tests/integration_test.py $(ASM_TARGET)

clean:
	rm -rf $(BUILD_DIR)
