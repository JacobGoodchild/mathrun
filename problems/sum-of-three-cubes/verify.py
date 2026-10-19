"""Independent check of a sum-of-three-cubes solution with exact integers.

Exit 0 = x^3 + y^3 + z^3 really equals k (a VERIFIED candidate: if k is
one of the seven open values below 1000 this would be a new result and
needs expert review), 1 = rejected.
"""
import json
import sys

OPEN = {114, 390, 627, 633, 732, 921, 975}


def check(k, x, y, z):
    try:
        k, x, y, z = (int(v) if isinstance(v, int) or str(v).lstrip("-").isdigit() else None
                      for v in (k, x, y, z))
    except (TypeError, ValueError):
        return 1, "not integers"
    if None in (k, x, y, z):
        return 1, "not integers"
    if x ** 3 + y ** 3 + z ** 3 != k:
        return 1, "%d^3 + %d^3 + %d^3 = %d, not %d" % (x, y, z, x ** 3 + y ** 3 + z ** 3, k)
    note = "k = %d is one of the seven OPEN cases below 1000" % k if k in OPEN else \
        "k = %d already had known solutions (a reproduction)" % k
    return 0, "%d^3 + %d^3 + %d^3 = %d exactly; %s" % (x, y, z, k, note)


if __name__ == "__main__":
    try:
        d = json.load(open(sys.argv[1]))["data"]
        code, msg = check(d["k"], d["x"], d["y"], d["z"])
    except Exception as e:
        code, msg = 1, "unreadable candidate: %r" % (e,)
    print(("VERIFIED: " if code == 0 else "REJECTED: ") + msg)
    sys.exit(code)
