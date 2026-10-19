MR_ROOT ?= ../..
CFLAGS = -O3 -Wall -Wextra -std=gnu11 -I$(MR_ROOT)/common
bin/toy: toy.c $(MR_ROOT)/common/mr.h
	mkdir -p bin
	$(CC) $(CFLAGS) -o $@ toy.c
clean:
	rm -rf bin
