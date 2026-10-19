MR_ROOT ?= ../..
include $(MR_ROOT)/common/bignum.mk
CFLAGS = -O3 -march=x86-64-v2 -Wall -Wextra -std=gnu11 -Wno-sign-compare -Wno-unused-parameter -I$(MR_ROOT)/common $(BIGNUM_CFLAGS)
bin/cuboid: cuboid.c $(MR_ROOT)/common/mr.h $(MR_ROOT)/common/bignum.h
	mkdir -p bin
	$(CC) $(CFLAGS) -o $@ cuboid.c $(BIGNUM_SRC) $(BIGNUM_LIBS)
clean:
	rm -rf bin
