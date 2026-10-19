/* Sums of three cubes: x^3 + y^3 + z^3 = k, Booker's method.
 *
 * Order a solution so |x| >= |y| >= |z| and put d = |x + y|. Booker
 * (2019) shows 0 < d < alpha |z| with alpha = 2^(1/3) - 1 (for |z| > sqrt k),
 * that d divides k - z^3, i.e. z^3 = k (mod d), and that
 *     Delta(d, z) = 3 d (4 |k - z^3| - d^3)
 * must be a perfect square (then x, y follow). So for each d we find all
 * cube roots of k modulo d, walk the arithmetic progressions z = r (mod d)
 * with 3d <= |z| <= Z (3 < 1/alpha, so this covers every possible z), and
 * test Delta for squareness modulo six tables of small moduli. The rare
 * survivors are printed as NOTE lines; plugin.py checks them exactly with
 * Python integers and only true solutions become candidates.
 *
 * Cube roots modulo d: factor d with a segmented sieve, take cube roots
 * modulo each prime (unique if p = 2 mod 3; a Tonelli-Shanks style
 * method if p = 1 mod 3), lift to prime powers (Hensel), combine (CRT).
 *
 * Usage: cubes k D0 D1 Z     (d in [D0, D1), |z| <= Z, Z < 2^64)
 */
#include "mr.h"

typedef unsigned __int128 u128;
typedef __int128 i128;
#define MAXF 16
#define MAXR 6561

static uint64_t mulmod(uint64_t a, uint64_t b, uint64_t m) { return (uint64_t)((u128)a * b % m); }
static uint64_t powmod(uint64_t a, u128 e, uint64_t m) {
    uint64_t r = 1 % m; a %= m;
    while (e) { if (e & 1) r = mulmod(r, a, m); a = mulmod(a, a, m); e >>= 1; }
    return r;
}
/* All cube roots of k modulo prime p. Returns count (0..3). */
static int cube_roots_p(int64_t k, uint64_t p, uint64_t *out) {
    uint64_t kk = (uint64_t)(((k % (int64_t)p) + (int64_t)p) % (int64_t)p);
    if (p == 2 || p == 3) { int n = 0; for (uint64_t z = 0; z < p; z++) if ((z * z * z) % p == kk) out[n++] = z; return n; }
    if (kk == 0) { out[0] = 0; return 1; }
    if (p % 3 == 2) { out[0] = powmod(kk, (2 * (u128)p - 1) / 3, p); return 1; }
    /* p = 1 mod 3 */
    if (powmod(kk, (p - 1) / 3, p) != 1) return 0;
    uint64_t t = p - 1; int s = 0;
    while (t % 3 == 0) { t /= 3; s++; }
    uint64_t g = 2;
    while (powmod(g, (p - 1) / 3, p) == 1) g++;
    uint64_t h = powmod(g, t, p);                 /* generates the 3-part, order 3^s */
    uint64_t gamma = h;
    for (int i = 0; i < s - 1; i++) gamma = powmod(gamma, 3, p);   /* order 3 */
    /* discrete log j of y = k^t in base h (Pohlig-Hellman, digits base 3) */
    uint64_t y = powmod(kk, t, p);
    u128 j = 0, pw3 = 1;
    uint64_t hinv = powmod(h, p - 2, p);
    for (int i = 0; i < s; i++) {
        uint64_t cur = mulmod(y, powmod(hinv, j, p), p);
        u128 e = 1;
        for (int q = 0; q < s - 1 - i; q++) e *= 3;
        uint64_t v = powmod(cur, e, p);
        int digit = v == 1 ? 0 : (v == gamma ? 1 : 2);
        j += digit * pw3;
        pw3 *= 3;
    }
    /* a = 3^{-1} mod t (t coprime to 3), 3a = 1 + c t */
    uint64_t a;
    if (t == 1) a = 0; else {
        i128 r0 = t, r1 = 3, s0 = 0, s1 = 1;
        while (r1) { i128 q = r0 / r1, tmp = r0 - q * r1; r0 = r1; r1 = tmp; tmp = s0 - q * s1; s0 = s1; s1 = tmp; }
        a = (uint64_t)(((s0 % (i128)t) + t) % t);
    }
    u128 c = ((u128)3 * a - 1) / (t ? t : 1);
    if (t == 1) c = 0;
    /* r = k^a * h^(-j c / 3) */
    u128 ex = (j * c / 3) % (((u128)p - 1));
    uint64_t r = mulmod(powmod(kk, a, p), powmod(hinv, ex, p), p);
    if (t == 1) {
        /* k in the 3-part itself: r = h^(j/3) */
        r = powmod(h, j / 3, p);
    }
    if (mulmod(mulmod(r, r, p), r, p) != kk) return -1;   /* internal error */
    out[0] = r; out[1] = mulmod(r, gamma, p); out[2] = mulmod(out[1], gamma, p);
    return 3;
}

/* lift roots mod p to mod p^e. k must not be 0 mod p and p != 3; p = 2 handled by brute lifting */
#define MAXLIFT 256
/* When p divides k (or p = 3) there can be many roots modulo p^e (e.g. z^3 = 0
 * mod 25 has 5), so up to MAXLIFT are kept and overflow is a hard error. */
static int lift(int64_t k, uint64_t p, int e, uint64_t *roots, int n, uint64_t *out) {
    uint64_t m = p;
    int cnt = n;
    uint64_t cur[MAXLIFT];
    for (int i = 0; i < n; i++) cur[i] = roots[i];
    for (int step = 1; step < e; step++) {
        uint64_t m2 = m * p;
        uint64_t kk = (uint64_t)(((k % (int64_t)m2) + (int64_t)m2) % (int64_t)m2);
        int c2 = 0;
        uint64_t nxt[MAXLIFT];
        for (int i = 0; i < cnt; i++)       /* try the p lifts r + j m (fine: p small when e > 1) */
            for (uint64_t jj = 0; jj < p; jj++) {
                uint64_t z = cur[i] + jj * m;
                if (mulmod(mulmod(z, z, m2), z, m2) == kk) {
                    if (c2 >= MAXLIFT) { fprintf(stderr, "too many lifted roots\n"); exit(7); }
                    nxt[c2++] = z;
                }
            }
        cnt = c2;
        for (int i = 0; i < cnt; i++) cur[i] = nxt[i];
        m = m2;
    }
    for (int i = 0; i < cnt; i++) out[i] = cur[i];
    return cnt;
}

static uint8_t *sq[6];
static const uint32_t MODS[6] = {2882880u, 6678671u, 3065857u, 12780049u, 409457u, 716539u};

static uint8_t *square_table(uint32_t m) {
    uint8_t *t = calloc(m, 1);
    for (uint64_t x = 0; x < m; x++) t[(x * x) % m] = 1;
    return t;
}

static inline int delta_maybe_square(int64_t k, uint64_t d, uint64_t az, int neg) {
    for (int i = 0; i < 6; i++) {
        uint64_t m = MODS[i];
        uint64_t zm = az % m, dm = d % m, km = (uint64_t)(((k % (int64_t)m) + (int64_t)m) % (int64_t)m);
        uint64_t z3 = zm * zm % m * zm % m;
        /* |k - z^3| = z^3 - k (z > 0) or k + |z|^3 (z < 0) */
        uint64_t ab = neg ? (km + z3) % m : (z3 + m - km) % m;
        uint64_t d3 = dm * dm % m * dm % m;
        uint64_t v = 3 * dm % m * ((4 * ab % m + m - d3) % m) % m;
        if (!sq[i][v]) return 0;
    }
    return 1;
}

int main(int argc, char **argv) {
    if (argc < 5) { fprintf(stderr, "usage: cubes k D0 D1 Z\n"); return 2; }
    int64_t k = atoll(argv[1]);
    uint64_t D0 = mr_parse_u64(argv[2]), D1 = mr_parse_u64(argv[3]), Z = mr_parse_u64(argv[4]);
    if (k < 1 || k > 1000 || D0 < 1 || D1 <= D0 || D1 > (1ULL << 62) || D1 - D0 > (1ULL << 26)) {
        fprintf(stderr, "bad arguments\n"); return 2;
    }
    for (int i = 0; i < 6; i++) sq[i] = square_table(MODS[i]);
    /* For k = 3 (mod 9) every cube is 1 (mod 9), so x = y = z = 1 (mod 3); for k = 6 (mod 9)
     * they are all 2 (mod 3). Then z = c3 (mod 3), and x + y = 2*c3 (mod 3) fixes the sign of
     * z for each d (since x + y has the sign of k - z^3, i.e. minus the sign of z once
     * |z| >= 11). This cuts the z values to check by about 6x (as in Booker-Sutherland). */
    int c3 = (k % 9 == 3) ? 1 : (k % 9 == 6) ? 2 : 0;
    /* primes up to sqrt(D1) */
    uint64_t lim = 1;
    while ((u128)lim * lim < D1) lim++;
    /* odd-only composite bitset: bit j stands for 2j+1 */
    uint64_t nbits = lim / 2 + 1;
    uint64_t *comp = calloc(nbits / 64 + 1, 8);
#define ISCOMP(n) ((comp[((n) >> 1) >> 6] >> (((n) >> 1) & 63)) & 1)
    for (uint64_t i = 3; i * i <= lim; i += 2)
        if (!ISCOMP(i)) for (uint64_t j = i * i; j <= lim; j += 2 * i) comp[(j >> 1) >> 6] |= 1ULL << ((j >> 1) & 63);
    const uint64_t W = 1 << 19;
    uint64_t *cof = malloc(8 * W);
    uint32_t (*fpw)[MAXF] = malloc(sizeof(uint32_t) * MAXF * W);
    uint8_t (*fex)[MAXF] = malloc(MAXF * W);
    uint8_t *nf = malloc(W);
    uint64_t dcount = 0, zcount = 0, notes = 0, withroots = 0;
    double t0 = mr_cpu_seconds();
    static uint64_t R[MAXR], R2[MAXR];
    for (uint64_t lo = D0; lo < D1; lo += W) {
        uint64_t hi = lo + W < D1 ? lo + W : D1, w = hi - lo;
        for (uint64_t i = 0; i < w; i++) { cof[i] = lo + i; nf[i] = 0; }
        for (uint64_t p = 2; p <= lim && p * p < hi; p += (p == 2 ? 1 : 2)) {
            if (p > 2 && ISCOMP(p)) continue;
            for (uint64_t x = (lo + p - 1) / p * p; x < hi; x += p) {
                uint64_t i = x - lo;
                int e = 0;
                while (cof[i] % p == 0) { cof[i] /= p; e++; }
                if (nf[i] < MAXF) { fpw[i][nf[i]] = (uint32_t)p; fex[i][nf[i]] = (uint8_t)e; nf[i]++; }
                else { fprintf(stderr, "too many prime factors\n"); return 6; }
            }
        }
        for (uint64_t i = 0; i < w; i++) {
            uint64_t d = lo + i;
            dcount++;
            /* k = +-3 mod 9 forces x = y = z = c3 (mod 3), so 3 never divides d = |x+y| */
            if (c3 && d >= 4 && d % 3 == 0) continue;
            int nfac = nf[i] + (cof[i] > 1);
            /* roots modulo d by CRT over prime powers */
            int nr = 1;
            uint64_t mod = 1;
            R[0] = 0;
            for (int f = 0; f < nfac && nr; f++) {
                uint64_t p = f < nf[i] ? fpw[i][f] : cof[i];
                int e = f < nf[i] ? fex[i][f] : 1;
                uint64_t pe = 1;
                for (int q = 0; q < e; q++) pe *= p;
                uint64_t rp[3], rpe[MAXLIFT];
                int c = cube_roots_p(k, p, rp);
                if (c < 0) { fprintf(stderr, "cube root failure p=%llu\n", (unsigned long long)p); return 4; }
                if (e > 1) c = lift(k, p, e, rp, c, rpe); else for (int q = 0; q < c; q++) rpe[q] = rp[q];
                if (!c) { nr = 0; break; }
                /* CRT combine R (mod mod) with rpe (mod pe) */
                /* inverse of mod modulo pe via extended Euclid */
                i128 r0 = (i128)pe, r1 = (i128)(mod % pe), s0 = 0, s1 = 1;
                while (r1) { i128 q = r0 / r1, tmp = r0 - q * r1; r0 = r1; r1 = tmp; tmp = s0 - q * s1; s0 = s1; s1 = tmp; }
                uint64_t minv = pe == 1 ? 0 : (uint64_t)(((s0 % (i128)pe) + pe) % pe);
                int n2 = 0;
                for (int a = 0; a < nr; a++)
                    for (int b = 0; b < c; b++) {
                        if (n2 >= MAXR) { fprintf(stderr, "too many roots\n"); return 5; }
                        /* x = R[a] + mod * ((rpe[b] - R[a]) * minv mod pe) */
                        uint64_t diff = (rpe[b] + pe - R[a] % pe) % pe;
                        uint64_t tq = mulmod(diff, minv, pe);
                        R2[n2++] = R[a] + mod * tq;
                    }
                mod *= pe;
                nr = n2;
                for (int a = 0; a < nr; a++) R[a] = R2[a];
            }
            if (!nr) continue;
            withroots++;
            /* walk z = r (mod d) over 3d <= |z| <= Z, both signs */
            u128 zlo = (u128)3 * d;
            if (zlo > Z) continue;
            int filt = c3 && zlo >= 11;
            int posok = !filt || (int)(d % 3) == c3, negok = !filt || (int)(d % 3) == (2 * c3) % 3;
            u128 step = filt ? (u128)3 * d : d;
            for (int a = 0; a < nr; a++) {
                uint64_t r = R[a] % d;
                /* positive z: smallest z >= zlo with z = r mod d (and z = c3 mod 3) */
                u128 z = zlo + ((r + d - (uint64_t)(zlo % d)) % d);
                if (filt) while (z % 3 != (u128)c3) z += d;
                for (; posok && z <= Z; z += step) {
                    zcount++;
                    if (delta_maybe_square(k, d, (uint64_t)z, 0)) {
                        notes++;
                        printf("NOTE {\"k\":%lld,\"d\":%llu,\"z\":%llu}\n", (long long)k, (unsigned long long)d,
                               (unsigned long long)z);
                    }
                }
                /* negative z: |z| = -z, -z = (d - r) mod d */
                uint64_t rn = (d - r) % d;
                z = zlo + ((rn + d - (uint64_t)(zlo % d)) % d);
                if (filt) while (z % 3 != (u128)((3 - c3) % 3)) z += d;
                for (; negok && z <= Z; z += step) {
                    zcount++;
                    if (delta_maybe_square(k, d, (uint64_t)z, 1)) {
                        notes++;
                        printf("NOTE {\"k\":%lld,\"d\":%llu,\"z\":-%llu}\n", (long long)k, (unsigned long long)d,
                               (unsigned long long)z);
                    }
                }
            }
        }
    }
    printf("DONE {\"cases\":%llu,\"with_roots\":%llu,\"z_checked\":%llu,\"survivors\":%llu,\"cpu\":%.2f}\n",
           (unsigned long long)dcount, (unsigned long long)withroots, (unsigned long long)zcount,
           (unsigned long long)notes, mr_cpu_seconds() - t0);
    return 0;
}
