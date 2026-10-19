/* Brocard's problem: is n! + 1 ever a perfect square for n > 7?
 *
 * Sieve test for a window of n values [A, B). If n!+1 = m^2 then n!+1 must
 * be a square (quadratic residue, or 0) modulo every prime p. Each prime
 * rules out about half of the n values that are left, so ~40-60 primes
 * clear a window of 10^8 numbers.
 *
 * The trick that makes this fast (as in Berndt & Galway): pick primes p
 * just ABOVE B. By Wilson's theorem (p-1)! = -1 (mod p), so
 *     n! = -1 / S(n),   S(n) = (n+1)(n+2)...(p-1)  (mod p)
 * and S(n-1) = S(n) * n. Walking n downwards costs ONE modular
 * multiplication per n per prime. Then
 *     n! + 1 = (S - 1) / S,   and   legendre((S-1)/S) = legendre(S(S-1)).
 * So n survives prime p iff jacobi(S(S-1), p) != -1.
 *
 * All arithmetic is in Montgomery form (R = 2^64, itself a square mod p,
 * so legendre(xR) = legendre(x) and we never convert back).
 *
 * Usage: brocard A B [maxprimes]
 * Prints CAND for any n surviving all primes (real solution or bug -
 * the independent verifier decides), then DONE.
 */
#include "mr.h"

typedef unsigned __int128 u128;

static uint64_t mulmod_slow(uint64_t a, uint64_t b, uint64_t m) { return (uint64_t)((u128)a * b % m); }

static uint64_t powmod_slow(uint64_t a, uint64_t e, uint64_t m) {
    uint64_t r = 1 % m;
    a %= m;
    while (e) { if (e & 1) r = mulmod_slow(r, a, m); a = mulmod_slow(a, a, m); e >>= 1; }
    return r;
}

/* Deterministic Miller-Rabin for all 64-bit n. */
static int is_prime_u64(uint64_t n) {
    static const uint64_t bases[] = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37};
    if (n < 2) return 0;
    for (int i = 0; i < 12; i++) { if (n == bases[i]) return 1; if (n % bases[i] == 0) return 0; }
    uint64_t d = n - 1; int s = 0;
    while (!(d & 1)) { d >>= 1; s++; }
    for (int i = 0; i < 12; i++) {
        uint64_t x = powmod_slow(bases[i], d, n);
        if (x == 1 || x == n - 1) continue;
        int ok = 0;
        for (int r = 1; r < s; r++) { x = mulmod_slow(x, x, n); if (x == n - 1) { ok = 1; break; } }
        if (!ok) return 0;
    }
    return 1;
}

/* Montgomery arithmetic modulo odd p < 2^63. */
typedef struct { uint64_t p, pinv, r1, r2; } mont_t;

static void mont_init(mont_t *M, uint64_t p) {
    M->p = p;
    uint64_t inv = p; /* Newton iteration for p^-1 mod 2^64 */
    for (int i = 0; i < 6; i++) inv *= 2 - p * inv;
    M->pinv = -inv;                          /* -p^-1 mod 2^64 */
    M->r1 = (uint64_t)(((u128)1 << 64) % p); /* R mod p  = Montgomery 1 */
    M->r2 = (uint64_t)((u128)M->r1 * M->r1 % p);
}

static inline uint64_t mont_mul(const mont_t *M, uint64_t a, uint64_t b) {
    u128 t = (u128)a * b;
    uint64_t m = (uint64_t)t * M->pinv;
    u128 u = (t + (u128)m * M->p) >> 64;
    uint64_t r = (uint64_t)u;
    return r >= M->p ? r - M->p : r;
}

static inline uint64_t to_mont(const mont_t *M, uint64_t x) { return mont_mul(M, x % M->p, M->r2); }

/* Jacobi symbol (a/n), n odd. Binary (Stein-style) algorithm written to be
 * branch-light: the swap compiles to conditional moves. Signs are tracked
 * as a single bit: (2/n) = -1 iff n = 3,5 mod 8 iff bit1 ^ bit2 of n;
 * reciprocity flips iff both numbers are 3 mod 4. */
static int jacobi(uint64_t a, uint64_t n) {
    unsigned t = 0;
    if (a >= n) a %= n;
    if (a == 0) return n == 1;
    int z = __builtin_ctzll(a);
    a >>= z;
    t ^= (unsigned)(z & ((n >> 1) ^ (n >> 2))) & 1u;
    while (a != n) {
        uint64_t lo = a < n ? a : n, hi = a < n ? n : a;
        t ^= (unsigned)((a < n) & ((a & n) >> 1)) & 1u; /* reciprocity on swap */
        a = hi - lo;
        n = lo;
        z = __builtin_ctzll(a);
        a >>= z;
        t ^= (unsigned)(z & ((n >> 1) ^ (n >> 2))) & 1u;
    }
    return n == 1 ? (t ? -1 : 1) : 0;
}

#ifdef JACOBI_TEST
static int jacobi_ref(uint64_t a, uint64_t n) {
    int t = 1;
    a %= n;
    while (a) {
        while (!(a & 1)) { a >>= 1; if ((n & 7) == 3 || (n & 7) == 5) t = -t; }
        uint64_t tmp = a; a = n; n = tmp;
        if ((a & 3) == 3 && (n & 3) == 3) t = -t;
        a %= n;
    }
    return n == 1 ? t : 0;
}
#endif

int main(int argc, char **argv) {
#ifdef JACOBI_TEST
    uint64_t x = 88172645463325252ULL;
    for (long i = 0; i < 20000000; i++) {
        x ^= x << 13; x ^= x >> 7; x ^= x << 17;
        uint64_t n = (x >> (x & 31)) | 1, a = x * 2654435761ULL >> (x & 7);
        if (i % 3 == 0) a = a % n;
        if (jacobi(a, n) != jacobi_ref(a, n)) { printf("MISMATCH %llu %llu\n", (unsigned long long)a, (unsigned long long)n); return 1; }
    }
    printf("jacobi ok\n");
    return 0;
#endif
    if (argc < 3) { fprintf(stderr, "usage: brocard A B [maxprimes]\n"); return 2; }
    uint64_t A = mr_parse_u64(argv[1]), B = mr_parse_u64(argv[2]);
    int maxprimes = argc > 3 ? (int)mr_parse_u64(argv[3]) : 200;
    if (A < 1 || B <= A || B > ((uint64_t)1 << 62)) { fprintf(stderr, "bad range\n"); return 2; }
    uint64_t L = B - A;
    if (L > 2000000000ULL) { fprintf(stderr, "window too big\n"); return 2; }
    /* one bit per n still alive */
    size_t words = (size_t)(L + 63) / 64;
    uint64_t *alive = malloc(words * 8);
    if (!alive) { fprintf(stderr, "out of memory\n"); return 3; }
    memset(alive, 0xff, words * 8);
#define ALIVE(o) ((alive[(o) >> 6] >> ((o) & 63)) & 1)
#define KILL(o) (alive[(o) >> 6] &= ~((uint64_t)1 << ((o) & 63)))
    uint64_t left = L, p = B, ops = 0;
    int used = 0;
    double t0 = mr_cpu_seconds();
    while (left > 0 && used < maxprimes) {
        do { p++; } while (!is_prime_u64(p));
        used++;
        mont_t M;
        mont_init(&M, p);
        /* S(B-1) = B * (B+1) * ... * (p-1) */
        uint64_t S = M.r1;
        for (uint64_t m = B; m < p; m++) S = mont_mul(&M, S, to_mont(&M, m));
        uint64_t nm = to_mont(&M, B - 1); /* n in Montgomery form, walking down */
        for (uint64_t n = B - 1;; n--) {
            uint64_t off = n - A;
            if (ALIVE(off)) {
                uint64_t sm1 = S >= M.r1 ? S - M.r1 : S + M.p - M.r1; /* S - 1 */
                uint64_t prod = mont_mul(&M, S, sm1);
                if (jacobi(prod, p) == -1) { KILL(off); left--; }
            }
            if (n == A) break;
            S = mont_mul(&M, S, nm);                    /* S(n-1) = S(n) * n */
            nm = nm >= M.r1 ? nm - M.r1 : nm + M.p - M.r1; /* n -> n-1 */
        }
        ops += L;
    }
    int ncand = 0;
    for (uint64_t off = 0; off < L && ncand < 20; off++)
        if (ALIVE(off)) {
            printf("CAND {\"kind\":\"solution\",\"summary\":\"n=%llu survives %d prime tests\","
                   "\"data\":{\"n\":%llu,\"primes_used\":%d}}\n",
                   (unsigned long long)(A + off), used, (unsigned long long)(A + off), used);
            ncand++;
        }
    printf("DONE {\"cases\":%llu,\"primes\":%d,\"survivors\":%llu,\"cpu\":%.3f}\n",
           (unsigned long long)L, used, (unsigned long long)left, mr_cpu_seconds() - t0);
    free(alive);
    return 0;
}
