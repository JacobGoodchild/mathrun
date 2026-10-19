/* Flip-graph search for matrix multiplication schemes over GF(2)
 * (Kauers & Moosbauer, "Flip graphs for matrix multiplication", 2022).
 *
 * A scheme of rank r for the <n,m,p> format is a list of r terms
 * (A_t, B_t, C_t), A_t an n x m 0/1 matrix, B_t m x p, C_t p x n, with
 *     sum_t A_t[i][j] B_t[j'][k] C_t[k'][i'] = [j=j'][k=k'][i=i']  (mod 2)
 * for all indices (the "Brent equations"). Each term is one multiplication.
 *
 * Moves (all keep the scheme correct):
 *  flip:   two terms sharing a factor, x(*)y(*)z + x(*)y'(*)z'
 *          -> x(*)y(*)(z+z') + x(*)(y'+y)(*)z'
 *  reduce: if a factor becomes 0, or two terms share two factors, the rank
 *          drops by one. This is how better schemes are found.
 *  plus:   rank + 1 move to escape a plateau (split a term in two).
 *
 * Usage: flipgraph n m p seed seconds startfile|- target
 *   startfile: "n m p r" then r lines "a b c" (bitmasks); "-" = standard
 *   algorithm (rank n*m*p). target: rank that would beat the record.
 * Output: BEST with the lowest-rank scheme found (always re-verified in C
 * first), CAND if rank < target, then DONE.
 */
#include "mr.h"

#define MAXR 512
static int N, M, P, R;
static uint64_t F[3][MAXR];           /* F[0]=A, F[1]=B, F[2]=C */
static uint64_t BF[3][MAXR];
static int BR;
static uint64_t rs[2];

static inline uint64_t rnd(void) {   /* xorshift128+ */
    uint64_t s1 = rs[0], s0 = rs[1];
    rs[0] = s0; s1 ^= s1 << 23;
    rs[1] = s1 ^ s0 ^ (s1 >> 17) ^ (s0 >> 26);
    return rs[1] + s0;
}
static inline int rndn(int n) { return (int)((rnd() >> 11) % (uint64_t)n); }

/* ---------- correctness check: rebuild the whole tensor ---------- */
static int scheme_ok(uint64_t (*f)[MAXR], int r) {
    int nm = N * M, mp = M * P;
    uint64_t *T = calloc((size_t)nm * mp, 8);
    for (int t = 0; t < r; t++)
        for (int u = 0; u < nm; u++) if (f[0][t] >> u & 1)
            for (int v = 0; v < mp; v++) if (f[1][t] >> v & 1)
                T[u * mp + v] ^= f[2][t];
    int ok = 1;
    for (int i = 0; i < N && ok; i++) for (int j = 0; j < M && ok; j++)
        for (int j2 = 0; j2 < M && ok; j2++) for (int k = 0; k < P && ok; k++) {
            uint64_t want = (j == j2) ? ((uint64_t)1 << (k * N + i)) : 0;
            if (T[(i * M + j) * mp + (j2 * P + k)] != want) ok = 0;
        }
    free(T);
    return ok;
}

static void standard(void) {
    R = 0;
    for (int i = 0; i < N; i++) for (int j = 0; j < M; j++) for (int k = 0; k < P; k++) {
        F[0][R] = (uint64_t)1 << (i * M + j);
        F[1][R] = (uint64_t)1 << (j * P + k);
        F[2][R] = (uint64_t)1 << (k * N + i);
        R++;
    }
}

static void remove_term(int t) {
    R--;
    for (int f = 0; f < 3; f++) F[f][t] = F[f][R];
}

/* Repeatedly apply reductions until none apply. O(r^2) but only called
 * when a quick check says a reduction exists. */
static void normalize(void) {
    int changed = 1;
    while (changed) {
        changed = 0;
        for (int t = 0; t < R; t++)
            if (!F[0][t] || !F[1][t] || !F[2][t]) { remove_term(t); changed = 1; t--; }
        for (int s = 0; s < R && !changed; s++)
            for (int t = s + 1; t < R && !changed; t++) {
                int e0 = F[0][s] == F[0][t], e1 = F[1][s] == F[1][t], e2 = F[2][s] == F[2][t];
                if (e0 + e1 + e2 < 2) continue;
                if (e0 && e1) F[2][s] ^= F[2][t];
                else if (e0 && e2) F[1][s] ^= F[1][t];
                else F[0][s] ^= F[0][t];
                remove_term(t);
                changed = 1;   /* term s may now be zero: loop again */
            }
    }
}

static int needs_reduce(int i) {
    if (!F[0][i] || !F[1][i] || !F[2][i]) return 1;
    for (int t = 0; t < R; t++) {
        if (t == i) continue;
        if ((F[0][t] == F[0][i]) + (F[1][t] == F[1][i]) + (F[2][t] == F[2][i]) >= 2) return 1;
    }
    return 0;
}

static int partners[MAXR];

/* one random flip; returns 1 if a flip happened */
static int try_flip(void) {
    int i = rndn(R), f = rndn(3), np = 0;
    uint64_t x = F[f][i];
    for (int t = 0; t < R; t++) if (t != i && F[f][t] == x) partners[np++] = t;
    if (!np) return 0;
    int j = partners[rndn(np)];
    if (rnd() & 1) { int tmp = i; i = j; j = tmp; }
    int g = (f + 1) % 3, h = (f + 2) % 3;
    F[h][i] ^= F[h][j];
    F[g][j] ^= F[g][i];
    if (needs_reduce(i) || needs_reduce(j)) normalize();
    return 1;
}

static void plus_move(void) {
    if (R + 1 >= MAXR) return;
    for (int tries = 0; tries < 100; tries++) {
        int i = rndn(R), j = rndn(R), f = rndn(3);
        int g = (f + 1) % 3, h = (f + 2) % 3;
        if (i == j || F[f][i] == F[f][j] || F[g][i] == F[g][j] || F[h][i] == F[h][j]) continue;
        /* x y z + x' y' z' = (x+x') y z + x' (y+y') z + x' y' (z+z')   (mod 2) */
        int k = R++;
        F[f][k] = F[f][j]; F[g][k] = F[g][i] ^ F[g][j]; F[h][k] = F[h][i];
        F[f][i] ^= F[f][j];
        F[h][j] ^= F[h][i];
        if (needs_reduce(i) || needs_reduce(j) || needs_reduce(k)) normalize();
        return;
    }
}

static void save_best(void) { BR = R; for (int f = 0; f < 3; f++) memcpy(BF[f], F[f], sizeof(uint64_t) * R); }
static void load_best(void) { R = BR; for (int f = 0; f < 3; f++) memcpy(F[f], BF[f], sizeof(uint64_t) * R); }

static void print_scheme(const char *tag, const char *kind, uint64_t (*f)[MAXR], int r) {
    printf("%s {\"kind\":\"%s\",\"summary\":\"<%d,%d,%d> rank %d over GF(2)\",\"rank\":%d,"
           "\"data\":{\"n\":%d,\"m\":%d,\"p\":%d,\"rank\":%d,\"field\":\"GF(2)\",\"terms\":[",
           tag, kind, N, M, P, r, r, N, M, P, r);
    for (int t = 0; t < r; t++)
        printf("%s[%llu,%llu,%llu]", t ? "," : "", (unsigned long long)f[0][t],
               (unsigned long long)f[1][t], (unsigned long long)f[2][t]);
    printf("]}}\n");
}

int main(int argc, char **argv) {
    if (argc < 8) { fprintf(stderr, "usage: flipgraph n m p seed seconds startfile|- target\n"); return 2; }
    N = atoi(argv[1]); M = atoi(argv[2]); P = atoi(argv[3]);
    uint64_t seed = mr_parse_u64(argv[4]);
    double budget = atof(argv[5]);
    int target = atoi(argv[7]);
    if (N < 1 || M < 1 || P < 1 || N * M > 64 || M * P > 64 || P * N > 64 || N * M * P >= MAXR) {
        fprintf(stderr, "format too large\n"); return 2;
    }
    rs[0] = seed * 0x9E3779B97F4A7C15ULL + 1; rs[1] = (seed ^ 0xD1B54A32D192ED03ULL) | 1;
    for (int i = 0; i < 20; i++) rnd();
    if (strcmp(argv[6], "-") == 0) standard();
    else {
        FILE *fp = fopen(argv[6], "r");
        int n2, m2, p2;
        if (!fp || fscanf(fp, "%d %d %d %d", &n2, &m2, &p2, &R) != 4 || n2 != N || m2 != M || p2 != P
            || R < 1 || R >= MAXR) { fprintf(stderr, "bad start file\n"); return 2; }
        for (int t = 0; t < R; t++) {
            unsigned long long a, b, c;
            if (fscanf(fp, "%llu %llu %llu", &a, &b, &c) != 3) { fprintf(stderr, "bad start file\n"); return 2; }
            F[0][t] = a; F[1][t] = b; F[2][t] = c;
        }
        fclose(fp);
    }
    if (!scheme_ok(F, R)) { fprintf(stderr, "start scheme is not correct\n"); return 3; }
    normalize();
    save_best();
    int start_rank = R;
    uint64_t flips = 0, plateau = 0, plus_count = 0, tries = 0, fails = 0;
    /* walk length before a plus move; grows with the rank like in Kauers-Moosbauer */
    uint64_t limit = 20000ULL * (uint64_t)R;
    double t0 = mr_cpu_seconds();
    while (1) {
        if ((++tries & 4095) == 0 && mr_cpu_seconds() - t0 > budget) break;
        if (!try_flip()) {
            /* no flip available from here at all (e.g. Strassen shares no factors) */
            if (++fails > 20000) { fails = 0; plateau = limit + 1; } else continue;
        } else { flips++; fails = 0; }
        if (R < BR) { save_best(); plateau = 0; if (BR < target) break; continue; }
        if (++plateau > limit) {
            plateau = 0;
            if (R > BR + 2 || ++plus_count % 8 == 0) load_best();  /* don't drift too far up */
            plus_move();
        }
    }
    if (R <= BR) save_best();  /* same rank: keep where the walk got to, so the next unit continues it */
    if (!scheme_ok(BF, BR)) { fprintf(stderr, "INTERNAL ERROR: best scheme fails check\n"); return 4; }
    print_scheme("BEST", "record", BF, BR);
    if (BR < target) print_scheme("CAND", "record", BF, BR);
    printf("DONE {\"cases\":%llu,\"start_rank\":%d,\"best_rank\":%d,\"plus\":%llu,\"cpu\":%.2f}\n",
           (unsigned long long)flips, start_rank, BR, (unsigned long long)plus_count, mr_cpu_seconds() - t0);
    return 0;
}
