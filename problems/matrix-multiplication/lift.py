"""Try to turn a GF(2) matrix multiplication scheme into one over the integers.

Records over GF(2) only count for ordinary numbers if they *lift*: the same
pattern of non-zero entries, with each 1 replaced by +1 or -1, satisfying
the Brent equations exactly over Z.

Write each entry as 1 - 2s with s in {0, 1}. Modulo 4 every Brent equation
becomes a LINEAR equation over GF(2) in the s variables (Hensel's first
step), so we solve that system, then test candidate sign choices exactly
over Z (any solution space vector, plus random kernel combinations).
Gauge symmetries (flipping the signs of two factors of one term) are fixed
first so the kernel is not needlessly large.
"""
import random


def _bits(x, size):
    return [b for b in range(size) if x >> b & 1]


def exact_over_z(n, m, p, sterms):
    """sterms: list of (A, B, C), each a dict position -> +1/-1. True if exact over Z."""
    acc = {}
    for A, B, C in sterms:
        for u, ua in A.items():
            i, j = divmod(u, m)
            for v, vb in B.items():
                j2, k = divmod(v, p)
                for w, wc in C.items():
                    k2, i2 = divmod(w, n)
                    key = (i, j, j2, k, k2, i2)
                    acc[key] = acc.get(key, 0) + ua * vb * wc
    want = {(i, j, j, k, k, i) for i in range(n) for j in range(m) for k in range(p)}
    for key, val in acc.items():
        if val != (1 if key in want else 0):
            return False
    return all(acc.get(key, 0) == 1 for key in want)


def lift(n, m, p, terms, tries=2000, seed=1):
    """Return a list of signed terms [[{pos: sign}, ...], ...] or None."""
    sizes = (n * m, m * p, p * n)
    var = {}            # (t, factor, pos) -> variable index
    fixed = set()
    for t, tri in enumerate(terms):
        for f in range(3):
            for b in _bits(tri[f], sizes[f]):
                var[(t, f, b)] = len(var)
        # gauge: lowest entry of A and of B in each term is +1
        for f in (0, 1):
            bs = _bits(tri[f], sizes[f])
            if bs:
                fixed.add(var[(t, f, bs[0])])
    nv = len(var)
    rows = []           # (bitmask of variables, rhs)
    want = {(i, j, j, k, k, i) for i in range(n) for j in range(m) for k in range(p)}
    contrib = {}
    for t, (a, b, c) in enumerate(terms):
        for u in _bits(a, sizes[0]):
            i, j = divmod(u, m)
            for v in _bits(b, sizes[1]):
                j2, k = divmod(v, p)
                for w in _bits(c, sizes[2]):
                    k2, i2 = divmod(w, n)
                    contrib.setdefault((i, j, j2, k, k2, i2), []).append((t, u, v, w))
    for key in set(contrib) | want:
        lst = contrib.get(key, [])
        N, d = len(lst), 1 if key in want else 0
        if (N - d) % 2:
            return None     # not even correct mod 2
        mask = 0
        for t, u, v, w in lst:
            for vi in (var[(t, 0, u)], var[(t, 1, v)], var[(t, 2, w)]):
                mask ^= 1 << vi
        rows.append((mask, ((N - d) // 2) % 2))
    for vi in fixed:
        rows.append((1 << vi, 0))
    # Gaussian elimination over GF(2)
    pivots = {}
    for mask, rhs in rows:
        for pc, (pm, pr) in pivots.items():
            if mask >> pc & 1:
                mask ^= pm
                rhs ^= pr
        if mask == 0:
            if rhs:
                return None   # inconsistent: no +-1 lift with this support
            continue
        pc = mask.bit_length() - 1
        for qc in list(pivots):
            qm, qr = pivots[qc]
            if qm >> pc & 1:
                pivots[qc] = (qm ^ mask, qr ^ rhs)
        pivots[pc] = (mask, rhs)
    free = [v for v in range(nv) if v not in pivots]
    rng = random.Random(seed)

    def solution(free_vals):
        s = [0] * nv
        for v, val in free_vals.items():
            s[v] = val
        for pc, (pm, pr) in pivots.items():
            val = pr
            for v in free:
                if pm >> v & 1 and s[v]:
                    val ^= 1
            s[pc] = val
        return s

    for attempt in range(tries):
        fv = {v: (0 if attempt == 0 else rng.getrandbits(1)) for v in free}
        s = solution(fv)
        sterms = []
        for t, tri in enumerate(terms):
            sterms.append(tuple({b: 1 - 2 * s[var[(t, f, b)]] for b in _bits(tri[f], sizes[f])}
                                for f in range(3)))
        if exact_over_z(n, m, p, sterms):
            return [[{str(k): v for k, v in fac.items()} for fac in st] for st in sterms]
        if not free:
            break
    return None
