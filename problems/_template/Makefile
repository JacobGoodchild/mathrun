MR_ROOT ?= ../..
# For big integers add:  include $(MR_ROOT)/common/bignum.mk  and link $(BIGNUM_SRC) $(BIGNUM_LIBS)
CFLAGS = -O3 -march=x86-64-v2 -Wall -Wextra -std=gnu11 -I$(MR_ROOT)/common
bin/searcher: searcher.c $(MR_ROOT)/common/mr.h
	mkdir -p bin
	$(CC) $(CFLAGS) -o $@ searcher.c
clean:
	rm -rf bin
