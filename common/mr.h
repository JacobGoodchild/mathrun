/* Small helpers shared by mathrun's C searchers.
 *
 * Protocol (stdout, one line each):
 *   CAND {json}   a candidate - the runner saves it, then verifies it
 *   BEST {json}   a new best for search-type problems
 *   NOTE {json}   anything else worth keeping
 *   DONE {json}   unit finished; must be last. No DONE = unit not counted.
 *
 * Time budgets use CPU time, so a paused (SIGSTOP) searcher doesn't
 * "use up" its budget while it sleeps.
 */
#ifndef MR_H
#define MR_H

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static inline double mr_cpu_seconds(void) {
    struct timespec ts;
    clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &ts);
    return (double)ts.tv_sec + ts.tv_nsec * 1e-9;
}

/* Parse an unsigned decimal string into unsigned __int128. Returns 0 on error. */
static inline int mr_parse_u128(const char *s, unsigned __int128 *out) {
    unsigned __int128 v = 0;
    if (!s || !*s) return 0;
    for (; *s; s++) {
        if (*s < '0' || *s > '9') return 0;
        unsigned __int128 nv = v * 10 + (unsigned)(*s - '0');
        if (nv / 10 != v) return 0; /* overflow */
        v = nv;
    }
    *out = v;
    return 1;
}

static inline int mr_parse_i128(const char *s, __int128 *out) {
    int neg = 0;
    unsigned __int128 u;
    if (*s == '-') { neg = 1; s++; }
    if (!mr_parse_u128(s, &u)) return 0;
    if (u > ((unsigned __int128)1 << 126)) return 0;
    *out = neg ? -(__int128)u : (__int128)u;
    return 1;
}

/* Write an unsigned __int128 as decimal into buf (>= 41 bytes). */
static inline char *mr_u128_str(unsigned __int128 v, char *buf) {
    char tmp[48];
    int n = 0;
    if (v == 0) tmp[n++] = '0';
    while (v) { tmp[n++] = (char)('0' + (int)(v % 10)); v /= 10; }
    for (int i = 0; i < n; i++) buf[i] = tmp[n - 1 - i];
    buf[n] = 0;
    return buf;
}

static inline char *mr_i128_str(__int128 v, char *buf) {
    if (v < 0) { buf[0] = '-'; mr_u128_str((unsigned __int128)(-v), buf + 1); }
    else mr_u128_str((unsigned __int128)v, buf);
    return buf;
}

static inline uint64_t mr_parse_u64(const char *s) {
    unsigned __int128 v;
    if (!mr_parse_u128(s, &v) || v > UINT64_MAX) {
        fprintf(stderr, "bad number: %s\n", s ? s : "(null)");
        exit(2);
    }
    return (uint64_t)v;
}

#endif
