/* Cap sets in F_3^n: as many points as possible with no three on a line.
 *
 * Three distinct points x, y, z of F_3^n are on a line exactly when
 * x + y + z = 0 (coordinatewise mod 3), so the third point on the line
 * through x and y is t(x, y) = -(x + y).
 *
 * Local search (simple, honest; records came from clever constructions):
 * keep, for every point p not in the cap, cnt[p] = number of pairs in the
 * cap whose third point is p. Points with cnt = 0 can be added. When none
 * can, swap: add a point with cnt = 1 and remove one point of the pair
 * that blocks it, or (sometimes) drop a random point. The best cap seen is
 * kept and printed (BEST); CAND if it beats the target size.
 *
 * Usage: capset n seed seconds startfile|- target
 *   startfile: list of point indices (base-3 numbers), one per line.
 */
#include "mr.h"

#define MAXN 9
static int n, N;
static int pw3[MAXN + 1];
static uint8_t *digits;          /* digits[p*n + i] */
static uint8_t *inS;
static int *cnt, *S, nS, *pos;
static int *best, nbest;
static uint64_t rs[2];

static inline uint64_t rnd(void) {
    uint64_t s1 = rs[0], s0 = rs[1];
    rs[0] = s0; s1 ^= s1 << 23;
    rs[1] = s1 ^ s0 ^ (s1 >> 17) ^ (s0 >> 26);
    return rs[1] + s0;
}

static inline int third(int x, int y) {
    const uint8_t *a = digits + (size_t)x * n, *b = digits + (size_t)y * n;
    int z = 0;
    for (int i = n - 1; i >= 0; i--) z = z * 3 + (6 - a[i] - b[i]) % 3;
    return z;
}

static void add(int p) {
    for (int i = 0; i < nS; i++) cnt[third(S[i], p)]++;
    pos[p] = nS; S[nS++] = p; inS[p] = 1;
}
static void del(int p) {
    int k = pos[p];
    S[k] = S[--nS]; pos[S[k]] = k; inS[p] = 0;
    for (int i = 0; i < nS; i++) cnt[third(S[i], p)]--;
}

static int is_cap(const int *pts, int m) {
    uint8_t *mark = calloc(N, 1);
    for (int i = 0; i < m; i++) { if (mark[pts[i]]) { free(mark); return 0; } mark[pts[i]] = 1; }
    for (int i = 0; i < m; i++)
        for (int j = i + 1; j < m; j++) {
            int t = third(pts[i], pts[j]);
            if (t != pts[i] && t != pts[j] && mark[t]) { free(mark); return 0; }
        }
    free(mark);
    return 1;
}

int main(int argc, char **argv) {
    if (argc < 6) { fprintf(stderr, "usage: capset n seed seconds startfile|- target\n"); return 2; }
    n = atoi(argv[1]);
    uint64_t seed = mr_parse_u64(argv[2]);
    double budget = atof(argv[3]);
    int target = atoi(argv[5]);
    if (n < 1 || n > MAXN) { fprintf(stderr, "bad n\n"); return 2; }
    pw3[0] = 1;
    for (int i = 1; i <= n; i++) pw3[i] = pw3[i - 1] * 3;
    N = pw3[n];
    digits = malloc((size_t)N * n);
    for (int p = 0; p < N; p++) for (int i = 0, q = p; i < n; i++, q /= 3) digits[(size_t)p * n + i] = q % 3;
    inS = calloc(N, 1); cnt = calloc(N, sizeof(int)); S = malloc(sizeof(int) * N); pos = malloc(sizeof(int) * N);
    best = malloc(sizeof(int) * N);
    rs[0] = seed * 0x9E3779B97F4A7C15ULL + 3; rs[1] = (seed ^ 0x94D049BB133111EBULL) | 1;
    for (int i = 0; i < 10; i++) rnd();
    if (strcmp(argv[4], "-")) {
        FILE *f = fopen(argv[4], "r");
        int p, m = 0;
        int *tmp = malloc(sizeof(int) * N);
        if (!f) { fprintf(stderr, "bad start file\n"); return 2; }
        while (fscanf(f, "%d", &p) == 1) { if (p < 0 || p >= N) { fprintf(stderr, "bad point\n"); return 2; } tmp[m++] = p; }
        fclose(f);
        if (!is_cap(tmp, m)) { fprintf(stderr, "start set is not a cap\n"); return 3; }
        for (int i = 0; i < m; i++) add(tmp[i]);
        free(tmp);
    }
    nbest = nS; memcpy(best, S, sizeof(int) * nS);
    int *freeL = malloc(sizeof(int) * N), *one = malloc(sizeof(int) * N);
    uint64_t steps = 0;
    double t0 = mr_cpu_seconds();
    while (mr_cpu_seconds() - t0 < budget) {
        for (int it = 0; it < 256; it++) {
            steps++;
            int nf = 0, no = 0;
            for (int p = 0; p < N; p++) if (!inS[p]) { if (!cnt[p]) freeL[nf++] = p; else if (cnt[p] == 1) one[no++] = p; }
            if (nf) { add(freeL[rnd() % nf]); }
            else if (no && (rnd() % 16)) {
                /* swap: add p (blocked once) and drop one point of its blocking pair */
                int p = one[rnd() % no], drop = -1;
                for (int i = 0; i < nS && drop < 0; i++) { int t = third(S[i], p); if (t != S[i] && inS[t]) drop = (rnd() & 1) ? S[i] : t; }
                if (drop >= 0) { del(drop); add(p); }
            } else if (nS) del(S[rnd() % nS]);
            if (nS > nbest) { nbest = nS; memcpy(best, S, sizeof(int) * nS); if (nbest > target) goto out; }
        }
    }
out:
    if (!is_cap(best, nbest)) { fprintf(stderr, "INTERNAL ERROR: best is not a cap\n"); return 4; }
    printf("BEST {\"summary\":\"cap of size %d in F_3^%d\",\"data\":{\"n\":%d,\"size\":%d,\"points\":[", nbest, n, n, nbest);
    for (int i = 0; i < nbest; i++) printf("%s%d", i ? "," : "", best[i]);
    printf("]}}\n");
    if (nbest > target) {
        printf("CAND {\"kind\":\"record\",\"summary\":\"cap of size %d in F_3^%d\",\"data\":{\"n\":%d,\"size\":%d,\"points\":[",
               nbest, n, n, nbest);
        for (int i = 0; i < nbest; i++) printf("%s%d", i ? "," : "", best[i]);
        printf("]}}\n");
    }
    printf("DONE {\"cases\":%llu,\"best\":%d,\"cpu\":%.2f}\n", (unsigned long long)steps, nbest, mr_cpu_seconds() - t0);
    return 0;
}
