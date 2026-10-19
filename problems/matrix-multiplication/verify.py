"""Independent verifier for matrix multiplication schemes over GF(2).

Rebuilds the whole tensor from the rank-one terms with plain Python sets
(a different method from the C searcher's word-level XOR) and checks it
equals the matrix multiplication tensor, i.e. that all Brent equations
hold mod 2. Also checks the rank really is below the record it claims.

Exit 0 = correct scheme with rank below the record (needs human review:
records over GF(2) do not always lift to integers, and the catalogue
should be re-checked), 1 = rejected, 2 = could not check.
"""
import json
import sys

# Kept separately from plugin.py on purpose: best known ranks (any ring /
# GF(2)-specific), Sedoglavic catalogue as read on 2026-10-19.
RECORDS = {(3, 3, 3): 23, (4, 4, 4): 47, (3, 4, 5): 47, (4, 4, 5): 61, (4, 5, 5): 76,
           (5, 5, 5): 93, (3, 3, 4): 29, (3, 3, 5): 36, (3, 4, 4): 38, (2, 4, 5): 32,
           (2, 5, 5): 40, (3, 5, 5): 58, (3, 3, 6): 40, (4, 4, 6): 73,
           (3, 3, 7): 49, (3, 6, 6): 80, (3, 4, 6): 54, (3, 5, 6): 68, (2, 5, 6): 47,
           (3, 4, 7): 63, (4, 4, 7): 85, (4, 5, 6): 90, (5, 5, 6): 110,
           (2, 2, 2): 7, (2, 2, 3): 11, (2, 3, 3): 15}


def positions(x, rows, cols):
    if not isinstance(x, int) or isinstance(x, bool) or x <= 0 or x >= 1 << (rows * cols):
        raise ValueError("factor %r out of range" % (x,))
    return [divmod(b, cols) for b in range(rows * cols) if (x >> b) & 1]


def is_matmul_scheme(n, m, p, terms):
    odd = set()
    for a, b, c in terms:
        for (i, j) in positions(a, n, m):
            for (j2, k) in positions(b, m, p):
                for (k2, i2) in positions(c, p, n):
                    odd ^= {(i, j, j2, k, k2, i2)}
    want = {(i, j, j, k, k, i) for i in range(n) for j in range(m) for k in range(p)}
    return odd == want


def integer_scheme_ok(n, m, p, signed, support):
    """Independent exact check over Z of a signed scheme with the same support."""
    if len(signed) != len(support):
        return False
    total = {}
    for (fa, fb, fc), (a, b, c) in zip(signed, support):
        A = {int(k): v for k, v in fa.items()}
        B = {int(k): v for k, v in fb.items()}
        C = {int(k): v for k, v in fc.items()}
        if set(A) != {q for q in range(n * m) if a >> q & 1} or set(B) != {q for q in range(m * p) if b >> q & 1} \
                or set(C) != {q for q in range(p * n) if c >> q & 1}:
            return False
        if any(v not in (1, -1) for d in (A, B, C) for v in d.values()):
            return False
        for u, x in A.items():
            for w2, y in B.items():
                for w3, z in C.items():
                    key = (u // m, u % m, w2 // p, w2 % p, w3 // n, w3 % n)
                    total[key] = total.get(key, 0) + x * y * z
    for i in range(n):
        for j in range(m):
            for j2 in range(m):
                for k in range(p):
                    for k2 in range(p):
                        for i2 in range(n):
                            want = 1 if (j == j2 and k == k2 and i == i2) else 0
                            if total.get((i, j, j2, k, k2, i2), 0) != want:
                                return False
    return True


def check(data, need_record=True):
    n, m, p = data["n"], data["m"], data["p"]
    terms = data["terms"]
    if data.get("field") != "GF(2)":
        return 1, "unknown field"
    if data["rank"] != len(terms):
        return 1, "claimed rank %s but %d terms" % (data["rank"], len(terms))
    if any(len(t) != 3 for t in terms):
        return 1, "malformed term"
    try:
        ok = is_matmul_scheme(n, m, p, terms)
    except ValueError as e:
        return 1, str(e)
    if not ok:
        return 1, "the terms do NOT multiply matrices correctly (Brent equations fail mod 2)"
    rec = RECORDS.get((n, m, p))
    msg = "correct <%d,%d,%d> scheme over GF(2) with %d multiplications" % (n, m, p, len(terms))
    if need_record:
        if rec is None:
            return 2, msg + "; no record on file for this format"
        if len(terms) >= rec:
            if len(terms) == rec and (n, m, p) in ((2, 2, 2), (2, 2, 3), (2, 3, 3), (3, 3, 3)):
                return 0, msg + " (equals the known value %d: a reproduction, not a record)" % rec
            return 1, msg + ", but that does not beat the record %d" % rec
        msg += ", BELOW the best known %d" % rec
        if data.get("integer_lift"):
            if not integer_scheme_ok(n, m, p, data["integer_lift"], terms):
                return 1, msg + ", but the claimed integer lift is WRONG"
            msg += "; the integer (+-1) version also checks out exactly over Z"
        else:
            msg += "; over GF(2) only (no integer lift found yet)"
        msg += ". Compare with the live catalogue before telling anyone"
    return 0, msg


if __name__ == "__main__":
    try:
        cand = json.load(open(sys.argv[1]))
        code, msg = check(cand["data"])
    except Exception as e:
        print("REJECTED: unreadable candidate: %r" % (e,))
        sys.exit(1)
    print(("VERIFIED: " if code == 0 else "REJECTED: " if code == 1 else "ERROR: ") + msg)
    sys.exit(code)
