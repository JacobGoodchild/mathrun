/* Template searcher: checks n in [A, B) for some property.
 * Speak the line protocol on stdout (see common/mr.h):
 *   CAND {json}  a candidate (saved, then checked by verify.py)
 *   DONE {json}  must be the last line; "cases" = how many things were checked */
#include "mr.h"

int main(int argc, char **argv) {
    if (argc < 3) { fprintf(stderr, "usage: searcher A B\n"); return 2; }
    uint64_t a = mr_parse_u64(argv[1]), b = mr_parse_u64(argv[2]);
    for (uint64_t n = a; n < b; n++) {
        if (0 /* replace with your test */)
            printf("CAND {\"kind\":\"solution\",\"summary\":\"n=%llu\",\"data\":{\"n\":%llu}}\n",
                   (unsigned long long)n, (unsigned long long)n);
    }
    printf("DONE {\"cases\":%llu}\n", (unsigned long long)(b - a));
    return 0;
}
