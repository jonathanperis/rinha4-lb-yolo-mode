CC ?= cc
BUILD_DIR := build
TARGET := $(BUILD_DIR)/rinha4-lb-yolo-mode
CFLAGS_WARN := -Wall -Wextra -Wshadow -Werror
CFLAGS_ARCH ?=
CFLAGS_COMMON := -std=c11 -O3 -DNDEBUG $(CFLAGS_ARCH) $(CFLAGS_WARN)
LDFLAGS_COMMON :=

.PHONY: all clean test

all: $(TARGET)

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(TARGET): src/yolo_lb.c | $(BUILD_DIR)
	$(CC) $(CFLAGS_COMMON) $< -o $@ $(LDFLAGS_COMMON)

test: $(TARGET)
	python3 tests/integration_test.py $(TARGET)

clean:
	rm -rf $(BUILD_DIR)
