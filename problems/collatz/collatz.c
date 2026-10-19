/* Collatz conjecture: check that every n in [A, B) eventually drops below
 * itself (all smaller numbers are already known to reach 1, so this shows
 * the whole range reaches 1). Uses the shortcut map T(n) = n/2 (n even),
 * (3n+1)/2 (n odd).
 *
 * Speed-up: a 2^K sieve. Write n = 2^K m + r. The first K steps of T only
 * depend on r, so T^K(n) = 3^a(r) m + T^K(r). Residues r whose trajectory
 * provably drops below n within K steps are skipped entirely; for the rest
 * we jump K steps at once and keep iterating with 128-bit integers.
 *
 * Usage: collatz A_hi A_lo count K
 *   start = A_hi * 2^64 + A_lo; checks [start, start + count), count a
 *   multiple of 2^K and start divisible by 2^K.
 * Output: CAND if some n fails to drop within MAXSTEPS steps (cycle or
 * divergence candidate), NOTE for 128-bit overflow (Python re-checks),
 * BEST with the longest glide in the range, then DONE.
 */
#include "mr.h"

typedef unsigned __int128 u128;
#define MAXSTEPS 100000
#define U128MAX (~(u128)0)

static uint32_t *res;      /* surviving residues */
static uint8_t *ra;        /* 3-exponent a(r) after K steps */
static uint64_t *rb;       /* T^K(r) (fits: < 3^K * 2 ) */
static uint16_t *rodd;     /* odd steps in first K, for standard-step counts */
static size_t nres;

static void build_sieve(int K, u128 nmin) {
    size_t cap = 1 << 20, n = 0;
    res = malloc(cap * 4); ra = malloc(cap); rb = malloc(cap * 8); rodd = malloc(cap * 2);
    for (uint64_t r = 0; r < ((uint64_t)1 << K); r++) {
        /* track T^j(n) = (3^a n + c) / 2^j symbolically for n = r (mod 2^K) */
        u128 c = 0, pow3 = 1;
        uint64_t v = r;     /* actual value of T^j(r) */
        int a = 0, dropped = 0;
        for (int j = 1; j <= K; j++) {
            if (v & 1) { v = (3 * v + 1) / 2; c = 3 * c + ((u128)1 << (j - 1)); pow3 *= 3; a++; }
            else v = v / 2;
            /* T^j(n) = (pow3 * n + c) / 2^j < n  <=>  n * (2^j - pow3) > c */
            u128 two = (u128)1 << j;
            if (pow3 < two && nmin * (two - pow3) > c) { dropped = 1; break; }
        }
        if (dropped) continue;
        if (n == cap) {
            cap *= 2;
            res = realloc(res, cap * 4); ra = realloc(ra, cap); rb = realloc(rb, cap * 8);
            rodd = realloc(rodd, cap * 2);
        }
        res[n] = (uint32_t)r; ra[n] = (uint8_t)a; rb[n] = v; rodd[n] = (uint16_t)a;
        n++;
    }
    nres = n;
}

int main(int argc, char **argv) {
    if (argc < 5) { fprintf(stderr, "usage: collatz A_hi A_lo count K\n"); return 2; }
    u128 start = ((u128)mr_parse_u64(argv[1]) << 64) | mr_parse_u64(argv[2]);
    uint64_t count = mr_parse_u64(argv[3]);
    int K = atoi(argv[4]);
    if (K < 4 || K > 30 || (count & (((uint64_t)1 << K) - 1)) || (start & ((((u128)1) << K) - 1))
        || start < ((u128)1 << (K + 8)) || start >= ((u128)1 << 96)
        || start + count < start) { fprintf(stderr, "bad arguments\n"); return 2; }
    build_sieve(K, start);
    u128 pow3[64];
    pow3[0] = 1;
    for (int i = 1; i < 64; i++) pow3[i] = pow3[i - 1] * 3;
    uint64_t mlo = (uint64_t)(start >> K), mcount = count >> K;
    uint64_t checked = 0, overflow = 0;
    int best_glide = -1;
    u128 best_n = 0;
    double t0 = mr_cpu_seconds();
    char b1[48], b2[48];
    for (uint64_t mi = 0; mi < mcount; mi++) {
        uint64_t m = mlo + mi;
        u128 base = (u128)m << K;
        for (size_t s = 0; s < nres; s++) {
            u128 n = base + res[s];
            u128 v = pow3[ra[s]] * m + rb[s];
            int steps = K, odd = rodd[s];
            while (v >= n) {
                if (v & 1) {
                    if (v > (U128MAX - 1) / 3) break;  /* would overflow */
                    v = (3 * v + 1) >> 1; odd++;
                } else v >>= 1;
                if (++steps > MAXSTEPS) break;
            }
            if (v >= n) {
                if (steps > MAXSTEPS) {
                    printf("CAND {\"kind\":\"solution\",\"summary\":\"n=%s did not drop below itself in %d steps\","
                           "\"data\":{\"n\":\"%s\"}}\n", mr_u128_str(n, b1), MAXSTEPS, mr_u128_str(n, b2));
                } else {
                    overflow++;
                    printf("NOTE {\"overflow\":\"%s\"}\n", mr_u128_str(n, b1));
                }
                continue;
            }
            int glide = steps + odd;  /* standard (3n+1, n/2) steps */
            if (glide > best_glide) { best_glide = glide; best_n = n; }
        }
        checked += nres;
    }
    printf("BEST {\"summary\":\"longest glide in unit: n=%s, %d steps\",\"n\":\"%s\",\"glide\":%d}\n",
           mr_u128_str(best_n, b1), best_glide, mr_u128_str(best_n, b2), best_glide);
    printf("DONE {\"cases\":%llu,\"iterated\":%llu,\"residues\":%zu,\"overflow\":%llu,\"cpu\":%.2f}\n",
           (unsigned long long)count, (unsigned long long)checked, nres,
           (unsigned long long)overflow, mr_cpu_seconds() - t0);
    return 0;
}
