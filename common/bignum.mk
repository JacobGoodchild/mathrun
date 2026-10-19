# Included by Makefiles of searchers that need big integers.
# ./mathrun install writes common/build/config.mk (GMP if present, else mini-gmp).
BIGNUM_CFLAGS = -I$(MR_ROOT)/common/vendor/mini-gmp
BIGNUM_LIBS =
BIGNUM_SRC = $(MR_ROOT)/common/vendor/mini-gmp/mini-gmp.c
-include $(MR_ROOT)/common/build/config.mk
