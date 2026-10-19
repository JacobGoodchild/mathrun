MR_ROOT ?= ../..
CFLAGS = -O3 -march=x86-64-v2 -Wall -Wextra -std=gnu11 -I$(MR_ROOT)/common
bin/magic: magic.c $(MR_ROOT)/common/mr.h
	mkdir -p bin
	$(CC) $(CFLAGS) -o $@ magic.c -lm
clean:
	rm -rf bin
