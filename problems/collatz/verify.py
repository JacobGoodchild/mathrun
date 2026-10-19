"""Independent check of a Collatz candidate with Python big integers.

A candidate is an n whose trajectory (standard map: n/2 or 3n+1) seemed
never to drop below n. We iterate up to 10^8 standard steps. If it drops
below n, the candidate is rejected (the searcher was wrong). If it does
not, it is reported as a verified candidate: an extraordinarily long
trajectory that experts must examine (cycle or divergence?).
"""
import json
import sys

LIMIT = 10 ** 8


def check(n):
    if not isinstance(n, int) or isinstance(n, bool) or n < 2:
        return 1, "bad n"
    v = n
    for step in range(LIMIT):
        if v < n:
            return 1, "n=%d drops below itself after %d steps; not a counterexample" % (n, step)
        v = 3 * v + 1 if v & 1 else v >> 1
    return 0, "n=%d stays >= itself for %d steps - needs expert review" % (n, LIMIT)


if __name__ == "__main__":
    try:
        n = int(json.load(open(sys.argv[1]))["data"]["n"])
    except Exception as e:
        print("REJECTED: unreadable candidate: %r" % (e,))
        sys.exit(1)
    code, msg = check(n)
    print(("VERIFIED: " if code == 0 else "REJECTED: ") + msg)
    sys.exit(code)
