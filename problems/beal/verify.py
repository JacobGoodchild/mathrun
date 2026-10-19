"""Independent check of a Beal counterexample with exact Python integers.

Needs A^x + B^y = C^z with A, B, C positive, x, y, z all >= 3 and
gcd(A, B, C) = 1. Exit 0 = verified candidate (would disprove Beal's
conjecture: needs expert review), 1 = rejected.
"""
import json
import math
import sys


def check(A, x, B, y, C, z):
    vals = (A, x, B, y, C, z)
    if not all(isinstance(v, int) and not isinstance(v, bool) for v in vals):
        return 1, "not all integers"
    if min(A, B, C) < 1:
        return 1, "bases must be positive"
    if min(x, y, z) < 3:
        return 1, "all exponents must be at least 3"
    if A ** x + B ** y != C ** z:
        return 1, "%d^%d + %d^%d != %d^%d" % vals
    if math.gcd(math.gcd(A, B), C) != 1:
        return 1, "true equation, but A, B, C share a factor (allowed by Beal)"
    return 0, "COUNTEREXAMPLE TO BEAL'S CONJECTURE: %d^%d + %d^%d = %d^%d, gcd 1" % vals


if __name__ == "__main__":
    try:
        d = json.load(open(sys.argv[1]))["data"]
        code, msg = check(d["A"], d["x"], d["B"], d["y"], d["C"], d["z"])
    except Exception as e:
        code, msg = 1, "unreadable candidate: %r" % (e,)
    print(("VERIFIED: " if code == 0 else "REJECTED: ") + msg)
    sys.exit(code)
