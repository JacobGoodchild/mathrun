/* Big integers: real GMP when ./mathrun install found it (fast), otherwise
 * the vendored mini-gmp (slower, same API subset). See CREDITS.md. */
#ifndef MR_BIGNUM_H
#define MR_BIGNUM_H
#ifdef MR_HAVE_GMP
#include <gmp.h>
#else
#include "mini-gmp.h"
#endif

static inline void mr_mpz_set_u128(mpz_t z, unsigned __int128 v) {
    mpz_set_ui(z, (unsigned long)(v >> 64));
    mpz_mul_2exp(z, z, 64);
    mpz_add_ui(z, z, (unsigned long)(uint64_t)v);
}
#endif
