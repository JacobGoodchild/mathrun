/* Toy searcher: scan n in [a, b) for (n * 2654435761) mod 2^32 == 0xDEADBEEF.
 * Exactly one n below 2^32 works (the multiplier is odd, so invertible).
 * Usage: toy A B [lie]   - "lie" makes it report a wrong answer (bug test). */
#include "mr.h"

int main(int argc, char **argv) {
    if (argc < 3) { fprintf(stderr, "usage: toy A B [lie]\n"); return 2; }
    uint64_t a = mr_parse_u64(argv[1]), b = mr_parse_u64(argv[2]);
    int lie = argc > 3 && strcmp(argv[3], "lie") == 0;
    for (uint64_t n = a; n < b; n++) {
        if ((uint32_t)(n * 2654435761u) == 0xDEADBEEFu)
            printf("CAND {\"kind\":\"solution\",\"summary\":\"n=%llu\",\"data\":{\"n\":%llu}}\n",
                   (unsigned long long)n, (unsigned long long)n);
    }
    if (lie) printf("CAND {\"kind\":\"solution\",\"summary\":\"n=%llu\",\"data\":{\"n\":%llu}}\n",
                    (unsigned long long)a, (unsigned long long)a);
    printf("DONE {\"cases\":%llu}\n", (unsigned long long)(b - a));
    return 0;
}
