"""Independent cap-set check (plain Python, coordinate vectors).

A cap: distinct points of F_3^n with no three on a line, i.e. no three
distinct x, y, z with x + y + z = 0 mod 3 in every coordinate.
Exit 0 = valid cap whose size beats the record in RECORDS (or any valid cap
when the dimension has no record on file, reported as a reproduction),
1 = rejected.
"""
import json
import sys

RECORDS = {7: 236, 8: 512}
KNOWN_MAX = {1: 2, 2: 4, 3: 9, 4: 20, 5: 45, 6: 112}


def vec(p, n):
    if not isinstance(p, int) or isinstance(p, bool) or not 0 <= p < 3 ** n:
        raise ValueError("bad point %r" % (p,))
    return tuple((p // 3 ** i) % 3 for i in range(n))


def check(n, size, points):
    if not isinstance(n, int) or not 1 <= n <= 9 or size != len(points):
        return 1, "bad dimension or size"
    try:
        vs = [vec(p, n) for p in points]
    except ValueError as e:
        return 1, str(e)
    s = set(vs)
    if len(s) != len(vs):
        return 1, "repeated point"
    for i in range(len(vs)):
        for j in range(i + 1, len(vs)):
            t = tuple((-(a + b)) % 3 for a, b in zip(vs[i], vs[j]))
            if t in s:
                return 1, "three points on a line: %s %s %s" % (vs[i], vs[j], t)
    if n in RECORDS:
        if size <= RECORDS[n]:
            return 1, "valid cap of size %d, but the record in F_3^%d is %d" % (size, n, RECORDS[n])
        return 0, "valid cap of size %d in F_3^%d, BEATING the best known %d - needs expert review" % (
            size, n, RECORDS[n])
    if n in KNOWN_MAX and size > KNOWN_MAX[n]:
        return 1, "impossible: the maximum in F_3^%d is %d" % (n, KNOWN_MAX[n])
    return 0, "valid cap of size %d in F_3^%d (reproduction)" % (size, n)


if __name__ == "__main__":
    try:
        d = json.load(open(sys.argv[1]))["data"]
        code, msg = check(d["n"], d["size"], d["points"])
    except Exception as e:
        code, msg = 1, "unreadable candidate: %r" % (e,)
    print(("VERIFIED: " if code == 0 else "REJECTED: ") + msg)
    sys.exit(code)
