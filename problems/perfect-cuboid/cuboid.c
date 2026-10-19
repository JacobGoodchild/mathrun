/* Perfect cuboid search by odd edge.
 *
 * A perfect cuboid has edges a, b, c with all four diagonals whole:
 * a^2+b^2, a^2+c^2, b^2+c^2 and a^2+b^2+c^2 all perfect squares. In a
 * primitive one exactly one edge is odd, so we search odd a in [A, B):
 *
 *  1. Factor every a in the block with a segmented sieve.
 *  2. Every even b with a^2 + b^2 = s^2 comes from a factorisation
 *     a^2 = u*v, u < v:  b = (v - u)/2. (These numbers can exceed 2^64.)
 *  3. Every primitive Euler brick (so every perfect cuboid) has: one edge
 *     divisible by 4 and another by 16, two edges divisible by 3 and one by
 *     9, one edge divisible by 5 and one by 11 (see README for sources; the
 *     tests check this against brute force). Legs are bucketed by these
 *     divisibilities so incompatible pairs are never even looked at.
 *  4. For each remaining pair of legs (b, c), test whether b^2 + c^2 is a square
 *     modulo three tables (moduli 2882880, 6678671, 3065857); the few that
 *     pass are checked exactly with big integers (an Euler brick), and then
 *     a^2 + b^2 + c^2 is checked exactly (a perfect cuboid -> CAND).
 *
 * Usage: cuboid A B   (A, B odd or even; only odd a are searched)
 */
#include "mr.h"
#include "bignum.h"

typedef unsigned __int128 u128;
#define MAXF 15
#define MAXD 200000

static const uint32_t M1 = 2882880u;          /* 64*63*65*11 */
static const uint32_t M2 = 6678671u;          /* 17*19*23*29*31 */
static uint8_t *sq1, *sq2, *sq3;
static uint32_t m3;

static uint8_t *square_table(uint32_t m) {
    uint8_t *t = calloc(m, 1);
    for (uint64_t x = 0; x < m; x++) t[(x * x) % m] = 1;
    return t;
}

static uint32_t *primes;
static size_t nprimes;

static void make_primes(uint64_t lim) {
    uint8_t *c = calloc(lim + 1, 1);
    primes = malloc(sizeof(uint32_t) * (lim / 2 + 10));
    for (uint64_t i = 2; i <= lim; i++) {
        if (c[i]) continue;
        primes[nprimes++] = (uint32_t)i;
        for (uint64_t j = i * i; j <= lim; j += i) c[j] = 1;
    }
    free(c);
}

typedef struct { uint64_t cof; uint8_t n; uint64_t p[MAXF]; uint8_t e[MAXF]; } fac_t;

/* divisibility mask: 1:3 2:9 4:5 8:11 16:4 32:16 */
static int mask_u128(u128 x) {
    return (x % 3 == 0) | ((x % 9 == 0) << 1) | ((x % 5 == 0) << 2) | ((x % 11 == 0) << 3) |
           ((x % 4 == 0) << 4) | ((x % 16 == 0) << 5);
}
static int mask_of(uint64_t x) { return mask_u128(x); }

/* can (a, b, c) with these masks be a primitive-or-scaled Euler brick? */
static int pair_ok(int ma, int mb, int mc) {
    int all = ma | mb | mc;
    int three = (ma & 1) + (mb & 1) + (mc & 1);
    if (three < 2 || !(all & 2) || !(all & 4) || !(all & 8)) return 0;
    return ((mb & 16) && (mc & 32)) || ((mc & 16) && (mb & 32));
}

static uint8_t lm[200000];
static int order[200000];
static u128 divs[MAXD];
static int nd;

static void gen_divisors(const fac_t *f, u128 limit) {
    /* all divisors u of a^2 with u < limit (limit = a) */
    nd = 1;
    divs[0] = 1;
    for (int i = 0; i < f->n; i++) {
        int cur = nd;
        u128 pk = 1;
        for (int k = 1; k <= 2 * f->e[i]; k++) {
            pk *= f->p[i];
            if (pk >= limit) break;
            for (int j = 0; j < cur; j++) {
                u128 d = divs[j] * pk;
                if (d < limit && nd < MAXD) divs[nd++] = d;
            }
        }
    }
}

int main(int argc, char **argv) {
    if (argc < 3) { fprintf(stderr, "usage: cuboid A B\n"); return 2; }
    uint64_t A = mr_parse_u64(argv[1]), B = mr_parse_u64(argv[2]);
    if (A < 3 || B <= A || B > ((uint64_t)1 << 62)) { fprintf(stderr, "bad range\n"); return 2; }
    sq1 = square_table(M1); sq2 = square_table(M2);
    m3 = 37u * 41u * 43u * 47u;  /* 3065857 */
    sq3 = square_table(m3);
    uint64_t lim = 2;
    while ((u128)lim * lim < B) lim++;
    make_primes(lim + 1);
    const uint64_t W = 1 << 16;
    fac_t *fac = malloc(sizeof(fac_t) * W);
    uint32_t *r1 = malloc(4 * MAXD), *r2 = malloc(4 * MAXD), *r3 = malloc(4 * MAXD);
    u128 *legs = malloc(sizeof(u128) * MAXD);
    uint64_t cases = 0, pairs = 0, notes = 0, maxlegs = 0, bricks = 0;
    mpz_t za, zb, zc, zs;
    mpz_init(za); mpz_init(zb); mpz_init(zc); mpz_init(zs);
    double t0 = mr_cpu_seconds();
    char sb[48], sc[48];
    for (uint64_t lo = A; lo < B; lo += W) {
        uint64_t hi = lo + W < B ? lo + W : B, w = hi - lo;
        for (uint64_t i = 0; i < w; i++) { fac[i].cof = lo + i; fac[i].n = 0; }
        for (size_t pi = 1; pi < nprimes; pi++) {   /* skip 2: only odd a are used */
            uint64_t p = primes[pi];
            if (p * p >= hi) break;
            uint64_t first = (lo + p - 1) / p * p;
            for (uint64_t x = first; x < hi; x += p) {
                fac_t *f = &fac[x - lo];
                int e = 0;
                while (f->cof % p == 0) { f->cof /= p; e++; }
                if (f->n < MAXF) { f->p[f->n] = p; f->e[f->n] = (uint8_t)e; f->n++; }
            }
        }
        for (uint64_t i = 0; i < w; i++) {
            uint64_t a = lo + i;
            if (!(a & 1)) continue;
            fac_t *f = &fac[i];
            if (f->cof > 1 && f->n < MAXF) { f->p[f->n] = f->cof; f->e[f->n] = 1; f->n++; }
            cases++;
            gen_divisors(f, a);
            if (nd >= MAXD) { fprintf(stderr, "too many divisors at a=%llu\n", (unsigned long long)a); return 3; }
            u128 a2 = (u128)a * a;
            int nl = 0;
            for (int j = 0; j < nd; j++) {
                u128 u = divs[j], v = a2 / u;
                u128 b = (v - u) / 2;   /* u, v odd, so v - u is even */
                if (b == 0) continue;
                legs[nl] = b;
                r1[nl] = (uint32_t)(b % M1); r2[nl] = (uint32_t)(b % M2); r3[nl] = (uint32_t)(b % m3);
                nl++;
            }
            if ((uint64_t)nl > maxlegs) maxlegs = nl;
            /* bucket legs by divisibility mask */
            int ma = mask_of(a);
            int cnt[64] = {0}, startb[65];
            for (int x = 0; x < nl; x++) { lm[x] = (uint8_t)mask_u128(legs[x]); cnt[lm[x]]++; }
            startb[0] = 0;
            for (int m = 0; m < 64; m++) startb[m + 1] = startb[m] + cnt[m];
            int fill[64];
            for (int m = 0; m < 64; m++) fill[m] = startb[m];
            for (int x = 0; x < nl; x++) order[fill[lm[x]]++] = x;
            for (int m1 = 0; m1 < 64; m1++) {
                if (!cnt[m1]) continue;
                for (int m2 = m1; m2 < 64; m2++) {
                    if (!cnt[m2] || !pair_ok(ma, m1, m2)) continue;
                    for (int xi = startb[m1]; xi < startb[m1 + 1]; xi++)
                        for (int yi = (m1 == m2 ? xi + 1 : startb[m2]); yi < startb[m2 + 1]; yi++) {
                            int x = order[xi], y = order[yi];
                            pairs++;
                            uint64_t s1 = ((uint64_t)r1[x] * r1[x] + (uint64_t)r1[y] * r1[y]) % M1;
                            if (!sq1[s1]) continue;
                            uint64_t s2 = ((uint64_t)r2[x] * r2[x] + (uint64_t)r2[y] * r2[y]) % M2;
                            if (!sq2[s2]) continue;
                            uint64_t s3 = ((uint64_t)r3[x] * r3[x] + (uint64_t)r3[y] * r3[y]) % m3;
                            if (!sq3[s3]) continue;
                            notes++;
                            /* exact: is b^2 + c^2 a square (Euler brick)? then a^2+b^2+c^2? */
                            mr_mpz_set_u128(zb, legs[x]);
                            mr_mpz_set_u128(zc, legs[y]);
                            mpz_mul(zs, zb, zb);
                            mpz_addmul(zs, zc, zc);
                            if (!mpz_perfect_square_p(zs)) continue;
                            bricks++;
                            mpz_set_ui(za, a);
                            mpz_addmul(zs, za, za);
                            if (!mpz_perfect_square_p(zs)) continue;
                            printf("CAND {\"kind\":\"solution\",\"summary\":\"perfect cuboid a=%llu b=%s c=%s\","
                                   "\"data\":{\"a\":\"%llu\",\"b\":\"%s\",\"c\":\"%s\"}}\n",
                                   (unsigned long long)a, mr_u128_str(legs[x], sb), mr_u128_str(legs[y], sc),
                                   (unsigned long long)a, sb, sc);
                            fflush(stdout);
                        }
                }
            }
        }
    }
    printf("DONE {\"cases\":%llu,\"euler_bricks\":%llu,\"pairs\":%llu,\"passed_filters\":%llu,\"max_legs\":%llu,\"cpu\":%.2f}\n",
           (unsigned long long)cases, (unsigned long long)bricks, (unsigned long long)pairs, (unsigned long long)notes,
           (unsigned long long)maxlegs, mr_cpu_seconds() - t0);
    return 0;
}
