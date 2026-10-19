"""Build good starting schemes for big formats from smaller ones.

Random walks from the schoolbook method get nowhere for big formats (e.g.
3x6x6 stays at 108). Records there are usually *constructions*: split one
dimension and add two smaller schemes, e.g. <3,6,6> = <3,3,6> + <3,3,6>.
We do the same with the best schemes found so far, and also use the
cyclic symmetry <n,m,p> -> <m,p,n> (terms (a,b,c) -> (b,c,a)).

Bit layout (same as flipgraph.c): A bit i*m+j, B bit j*p+k, C bit k*n+i.
"""


def standard(n, m, p):
    return [[1 << (i * m + j), 1 << (j * p + k), 1 << (k * n + i)]
            for i in range(n) for j in range(m) for k in range(p)]


def rotate(terms):
    """scheme for <n,m,p>  ->  scheme for <m,p,n>"""
    return [[b, c, a] for a, b, c in terms]


def _remap(x, rows, cols, f):
    out = 0
    for bit in range(rows * cols):
        if x >> bit & 1:
            r, c = divmod(bit, cols)
            out |= 1 << f(r, c)
    return out


def embed(terms, sub, full, off):
    """Place a scheme for sub-format `sub` inside `full`, shifted by `off` = (oi, oj, ok)."""
    n1, m1, p1 = sub
    n, m, p = full
    oi, oj, ok = off
    out = []
    for a, b, c in terms:
        A = _remap(a, n1, m1, lambda i, j: (i + oi) * m + (j + oj))
        B = _remap(b, m1, p1, lambda j, k: (j + oj) * p + (k + ok))
        C = _remap(c, p1, n1, lambda k, i: (k + ok) * n + (i + oi))
        out.append([A, B, C])
    return out


def best_start(fmt, stored, depth=3, memo=None):
    """Lowest-rank scheme we can build for fmt. stored: {(n,m,p): terms}."""
    memo = {} if memo is None else memo
    key = (fmt, depth)
    if key in memo:
        return memo[key]
    n, m, p = fmt
    best = standard(n, m, p)
    # stored scheme for this format or a cyclic rotation of it
    for rot in range(3):
        src = [(n, m, p), (p, n, m), (m, p, n)][rot]   # format whose rotation(s) give fmt
        if src in stored:
            t = stored[src]
            for _ in range(rot):
                t = rotate(t)
            if len(t) < len(best):
                best = t
    if depth > 0:
        for axis in range(3):
            d = fmt[axis]
            for d1 in range(1, d // 2 + 1):
                d2 = d - d1
                s1 = list(fmt); s1[axis] = d1
                s2 = list(fmt); s2[axis] = d2
                t1 = best_start(tuple(s1), stored, depth - 1, memo)
                t2 = best_start(tuple(s2), stored, depth - 1, memo)
                if len(t1) + len(t2) >= len(best):
                    continue
                off2 = [0, 0, 0]; off2[axis] = d1
                best = embed(t1, tuple(s1), fmt, (0, 0, 0)) + embed(t2, tuple(s2), fmt, tuple(off2))
    memo[key] = best
    return best
