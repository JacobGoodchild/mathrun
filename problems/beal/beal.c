/* Beal conjecture search: A^x + B^y = C^z with x, y, z >= 3 and
 * gcd(A, B, C) = 1 has no solutions (Beal, US$1,000,000 prize).
 *
 * Search space for this program: all bases A, B, C <= CMAX and exponents
 * x, y, z in [XMIN, XMAX]. Each run handles A in [A0, A1) with every
 * B <= A (the sum is symmetric, so this covers every pair of bases) and
 * every x, y.
 *
 * Method (as Norvig's, but modular): put C^z mod p, p = 2^61 - 1, for all
 * C <= CMAX and z into a hash table (32-bit fingerprints). For each A, B,
 * x, y look up (A^x + B^y) mod p. A hit is re-checked exactly with big
 * integers; exact solutions with gcd > 1 (like 2^3 + 2^3 = 2^4) are
 * counted, coprime ones are candidates.
 *
 * Usage: beal A0 A1 CMAX [XMIN XMAX]
 */
#include "mr.h"
#include "bignum.h"
#include <math.h>

typedef unsigned __int128 u128;
static const uint64_t P = (1ULL << 61) - 1;

static inline uint64_t mulp(uint64_t a, uint64_t b) {
    u128 t = (u128)a * b;
    uint64_t lo = (uint64_t)t & P, hi = (uint64_t)(t >> 61);
    uint64_t r = lo + hi;
    return r >= P ? r - P : r;
}
static inline uint64_t addp(uint64_t a, uint64_t b) { uint64_t r = a + b; return r >= P ? r - P : r; }

static uint32_t *tab;
static int tbits;
static uint64_t tmask;
static inline uint64_t slot(uint64_t s) { return (s * 0x9E3779B97F4A7C15ULL) >> (64 - tbits); }
static inline uint32_t fp(uint64_t s) { return (uint32_t)((s * 0xD6E8FEB86659FD93ULL) >> 32) | 1u; }
/* small bit filter (fits in cache) checked before the big table */
static uint64_t *bloom;
static int bbits;
static inline uint64_t bslot(uint64_t s) { return (s * 0xA0761D6478BD642FULL) >> (64 - bbits); }

static void insert(uint64_t s) {
    uint64_t b = bslot(s);
    bloom[b >> 6] |= 1ULL << (b & 63);
    uint64_t i = slot(s);
    uint32_t f = fp(s);
    while (tab[i] && tab[i] != f) i = (i + 1) & tmask;
    tab[i] = f;
}
static inline int lookup(uint64_t s) {
    uint64_t b = bslot(s);
    if (!((bloom[b >> 6] >> (b & 63)) & 1)) return 0;
    uint64_t i = slot(s);
    uint32_t f = fp(s);
    while (tab[i]) { if (tab[i] == f) return 1; i = (i + 1) & tmask; }
    return 0;
}

static uint64_t gcd64(uint64_t a, uint64_t b) { while (b) { uint64_t t = a % b; a = b; b = t; } return a; }

static uint64_t exact_hits = 0, nontrivial = 0, false_hits = 0;
static uint64_t CMAX;
static int XMIN, XMAX;

/* exact re-check of A^x + B^y = C^z for some C <= CMAX, z in range */
static void check_exact(uint64_t A, int x, uint64_t B, int y) {
    mpz_t s, t, c;
    mpz_init(s); mpz_init(t); mpz_init(c);
    mpz_ui_pow_ui(s, A, x);
    mpz_ui_pow_ui(t, B, y);
    mpz_add(s, s, t);
    int found = 0;
    for (int z = XMIN; z <= XMAX; z++) {
        if (!mpz_root(c, s, z)) continue;          /* exact z-th root? */
        if (mpz_cmp_ui(c, CMAX) > 0) continue;
        uint64_t C = mpz_get_ui(c);
        found = 1;
        exact_hits++;
        if (gcd64(gcd64(A, B), C) == 1) {
            nontrivial++;
            printf("CAND {\"kind\":\"solution\",\"summary\":\"%llu^%d + %llu^%d = %llu^%d with gcd 1\","
                   "\"data\":{\"A\":%llu,\"x\":%d,\"B\":%llu,\"y\":%d,\"C\":%llu,\"z\":%d}}\n",
                   (unsigned long long)A, x, (unsigned long long)B, y, (unsigned long long)C, z,
                   (unsigned long long)A, x, (unsigned long long)B, y, (unsigned long long)C, z);
            fflush(stdout);
        }
    }
    if (!found) false_hits++;
    mpz_clear(s); mpz_clear(t); mpz_clear(c);
}

int main(int argc, char **argv) {
    if (argc < 4) { fprintf(stderr, "usage: beal A0 A1 CMAX [XMIN XMAX]\n"); return 2; }
    uint64_t A0 = mr_parse_u64(argv[1]), A1 = mr_parse_u64(argv[2]);
    CMAX = mr_parse_u64(argv[3]);
    XMIN = argc > 4 ? atoi(argv[4]) : 3;
    XMAX = argc > 5 ? atoi(argv[5]) : 7;
    if (A0 < 1 || A1 <= A0 || A1 - 1 > CMAX || CMAX > (1ULL << 24) || XMIN < 3 || XMAX < XMIN || XMAX > 40) {
        fprintf(stderr, "bad arguments\n"); return 2;
    }
    int nz = XMAX - XMIN + 1;
    uint64_t entries = CMAX * (uint64_t)nz;
    tbits = 1;
    while ((1ULL << tbits) < 3 * entries) tbits++;
    tmask = (1ULL << tbits) - 1;
    tab = calloc((size_t)1 << tbits, 4);
    bbits = tbits + 3;   /* ~8 bits per entry in the filter: ~1 in 9 pass falsely... */
    while (bbits > 27) bbits--;   /* keep it at most 16 MB so it stays in cache */
    bloom = calloc(((size_t)1 << bbits) / 64, 8);
    if (!tab) { fprintf(stderr, "out of memory\n"); return 3; }
    for (uint64_t C = 1; C <= CMAX; C++) {
        uint64_t v = mulp(mulp(C, C), C);   /* C^3 */
        for (int z = 3; z <= XMAX; z++) {
            if (z >= XMIN) insert(v);
            v = mulp(v, C);
        }
    }
    uint64_t pairs = 0;
    double t0 = mr_cpu_seconds();
    uint64_t ax[41], by[41];
    for (uint64_t A = A0; A < A1; A++) {
        uint64_t v = mulp(mulp(A, A), A);
        for (int x = 3; x <= XMAX; x++) { ax[x] = v; v = mulp(v, A); }
        for (uint64_t B = 1; B <= A; B++) {
            uint64_t w = mulp(mulp(B, B), B);
            for (int y = 3; y <= XMAX; y++) { by[y] = w; w = mulp(w, B); }
            for (int x = XMIN; x <= XMAX; x++)
                for (int y = XMIN; y <= XMAX; y++)
                    if (lookup(addp(ax[x], by[y]))) check_exact(A, x, B, y);
        }
        pairs += A;
    }
    printf("DONE {\"cases\":%llu,\"exact_hits\":%llu,\"coprime\":%llu,\"false_hits\":%llu,\"cpu\":%.2f}\n",
           (unsigned long long)pairs, (unsigned long long)exact_hits, (unsigned long long)nontrivial,
           (unsigned long long)false_hits, mr_cpu_seconds() - t0);
    return 0;
}
