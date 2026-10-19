/* 3x3 magic square of nine distinct squares.
 *
 * Every 3x3 magic square has the form
 *     c+a    c-a-b  c+b
 *     c-a+b  c      c+a-b
 *     c-b    c+a+b  c-a
 * and for one made of squares the centre c is a square, c = e^2, and every
 * prime factor of e is 1 mod 4 (see README). Each pair c-x, c+x of
 * squares corresponds to 2e^2 = p^2 + q^2 with x = (q^2 - p^2)/2. So:
 *   1. factor e (sieve); skip unless all prime factors are 1 mod 4;
 *   2. list every way of writing 2e^2 = p^2 + q^2 using Gaussian
 *      integers (each p = pi * conj(pi) is split with Cornacchia);
 *   3. X = the set of x values; look for a > b in X with a+b and a-b in X.
 * a, b, a+b in X gives seven squares (centre + three full pairs; counted
 * as three_pairs); all four gives the full nine -> CAND.
 *
 * Usage: magic E0 E1   (searches e in [E0, E1))
 */
#include "mr.h"
#include <math.h>

typedef __int128 i128;
typedef unsigned __int128 u128;
#define MAXF 16
#define MAXX 20000

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

static uint64_t mulmod(uint64_t a, uint64_t b, uint64_t m) { return (uint64_t)((u128)a * b % m); }
static uint64_t powmod(uint64_t a, uint64_t e, uint64_t m) {
    uint64_t r = 1; a %= m;
    while (e) { if (e & 1) r = mulmod(r, a, m); a = mulmod(a, a, m); e >>= 1; }
    return r;
}
static uint64_t isqrt64(uint64_t n) {
    uint64_t r = (uint64_t)sqrtl((long double)n);
    while (r * r > n) r--;
    while ((r + 1) * (r + 1) <= n) r++;
    return r;
}

/* p = 1 mod 4 prime: find u > v > 0 with u^2 + v^2 = p (Cornacchia). */
static void two_squares(uint64_t p, int64_t *u, int64_t *v) {
    uint64_t t = 0;
    for (uint64_t g = 2;; g++) {
        t = powmod(g, (p - 1) / 4, p);
        if (mulmod(t, t, p) == p - 1) break;
    }
    uint64_t a = p, b = t > p / 2 ? p - t : t, lim = isqrt64(p);
    while (b > lim) { uint64_t r = a % b; a = b; b = r; }
    *u = (int64_t)b;
    *v = (int64_t)isqrt64(p - b * b);
}

typedef struct { i128 re, im; } gauss;
static inline gauss gmul(gauss x, gauss y) {
    gauss z = { x.re * y.re - x.im * y.im, x.re * y.im + x.im * y.re };
    return z;
}

static uint64_t X[MAXX];
static int nx;
static int cmp64(const void *a, const void *b) {
    uint64_t x = *(const uint64_t *)a, y = *(const uint64_t *)b;
    return x < y ? -1 : x > y;
}
static int inX(uint64_t v) {
    int lo = 0, hi = nx - 1;
    while (lo <= hi) { int mid = (lo + hi) / 2; if (X[mid] == v) return 1; if (X[mid] < v) lo = mid + 1; else hi = mid - 1; }
    return 0;
}

int main(int argc, char **argv) {
    if (argc < 3) { fprintf(stderr, "usage: magic E0 E1\n"); return 2; }
    uint64_t E0 = mr_parse_u64(argv[1]), E1 = mr_parse_u64(argv[2]);
    int dump = argc > 3 && strcmp(argv[3], "dumpx") == 0;  /* testing: print X for each e */
    if (E0 < 1 || E1 <= E0 || E1 > 3000000000000ULL) { fprintf(stderr, "bad range\n"); return 2; }
    uint64_t lim = isqrt64(E1) + 2;
    make_primes(lim);
    const uint64_t W = 1 << 16;
    uint64_t *cof = malloc(8 * W);
    uint8_t *bad = malloc(W);
    uint32_t (*fp)[MAXF] = malloc(sizeof(uint32_t) * MAXF * W);
    uint8_t (*fe)[MAXF] = malloc(MAXF * W);
    uint8_t *nf = malloc(W);
    uint64_t cases = 0, eligible = 0, three = 0;
    int maxx = 0;
    double t0 = mr_cpu_seconds();
    for (uint64_t lo = E0; lo < E1; lo += W) {
        uint64_t hi = lo + W < E1 ? lo + W : E1, w = hi - lo;
        for (uint64_t i = 0; i < w; i++) { cof[i] = lo + i; bad[i] = 0; nf[i] = 0; }
        for (size_t pi = 0; pi < nprimes; pi++) {
            uint64_t p = primes[pi];
            if (p * p >= hi) break;
            uint64_t first = (lo + p - 1) / p * p;
            for (uint64_t x = first; x < hi; x += p) {
                uint64_t i = x - lo;
                if (p % 4 != 1) { bad[i] = 1; continue; }
                if (bad[i]) continue;
                int k = 0;
                while (cof[i] % p == 0) { cof[i] /= p; k++; }
                if (nf[i] < MAXF) { fp[i][nf[i]] = (uint32_t)p; fe[i][nf[i]] = (uint8_t)k; nf[i]++; }
                else bad[i] = 2;  /* cannot happen below 3e12; flagged below */
            }
        }
        for (uint64_t i = 0; i < w; i++) {
            uint64_t e = lo + i;
            cases++;
            if (bad[i] == 2) { fprintf(stderr, "too many factors at %llu\n", (unsigned long long)e); return 3; }
            if (bad[i] || e == 1) continue;
            /* the cofactor left over is 1 or a prime > sqrt(e) */
            uint64_t big = cof[i];
            if (big > 1 && big % 4 != 1) continue;
            eligible++;
            /* Gaussian prime above each p: build all products  (1+i) * prod pi^s conj(pi)^(2k-s) */
            int np = nf[i] + (big > 1);
            gauss pis[MAXF + 1];
            int ks[MAXF + 1];
            for (int j = 0; j < np; j++) {
                uint64_t p = j < nf[i] ? fp[i][j] : big;
                int64_t u, v;
                two_squares(p, &u, &v);
                pis[j].re = u; pis[j].im = v;
                ks[j] = j < nf[i] ? fe[i][j] : 1;
            }
            /* enumerate exponent choices with an odometer */
            int s[MAXF + 1] = {0};
            nx = 0;
            for (;;) {
                gauss z = {1, 1};
                for (int j = 0; j < np; j++) {
                    gauss pc = {pis[j].re, -pis[j].im};
                    for (int t = 0; t < s[j]; t++) z = gmul(z, pis[j]);
                    for (int t = 0; t < 2 * ks[j] - s[j]; t++) z = gmul(z, pc);
                }
                i128 P = z.re < 0 ? -z.re : z.re, Q = z.im < 0 ? -z.im : z.im;
                if (P > Q) { i128 tmp = P; P = Q; Q = tmp; }
                if (P > 0 && P != Q && nx < MAXX) X[nx++] = (uint64_t)((Q * Q - P * P) / 2);
                int j = 0;
                while (j < np && ++s[j] > 2 * ks[j]) { s[j] = 0; j++; }
                if (j == np) break;
            }
            qsort(X, nx, 8, cmp64);
            int m = 0;
            for (int k = 0; k < nx; k++) if (!m || X[k] != X[m - 1]) X[m++] = X[k];
            nx = m;
            if (nx > maxx) maxx = nx;
            if (dump) {
                printf("NOTE {\"e\":%llu,\"x\":[", (unsigned long long)e);
                for (int k = 0; k < nx; k++) printf("%s%llu", k ? "," : "", (unsigned long long)X[k]);
                printf("]}\n");
            }
            for (int ia = 0; ia < nx; ia++)
                for (int ib = 0; ib < ia; ib++) {
                    uint64_t a = X[ia], b = X[ib];
                    if (!inX(a + b)) continue;
                    if (a == 2 * b) continue;   /* a-b = b would repeat an entry */
                    three++;
                    if (inX(a - b)) {
                        u128 c = (u128)e * e;
                        char cs[48];
                        printf("CAND {\"kind\":\"solution\",\"summary\":\"magic square of squares, centre %s\","
                               "\"data\":{\"e\":%llu,\"a\":%llu,\"b\":%llu}}\n", mr_u128_str(c, cs),
                               (unsigned long long)e, (unsigned long long)a, (unsigned long long)b);
                    }
                }
        }
    }
    printf("DONE {\"cases\":%llu,\"eligible\":%llu,\"three_pairs\":%llu,\"max_x\":%d,\"cpu\":%.2f}\n",
           (unsigned long long)cases, (unsigned long long)eligible, (unsigned long long)three, maxx,
           mr_cpu_seconds() - t0);
    return 0;
}
