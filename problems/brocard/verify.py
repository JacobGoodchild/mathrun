"""Independent verifier for Brocard candidates.

Written separately from the C searcher and works differently:
* small n (<= 3000): computes n! + 1 exactly and checks it is a square;
* large n: uses 64 *different* primes q a little above n, computes n! mod q
  directly from Wilson's theorem with plain Python integers, and applies
  Euler's criterion (pow) instead of a Jacobi-symbol routine.

Exit 0 = verified candidate, 1 = rejected, 2 = could not check.
For large n a pass means "n! + 1 is a square modulo 64 further primes",
which a non-square would survive with probability about 2^-64. It is
strong evidence, not a proof; a human would need to look further.
"""
import json
import math
import sys


def is_probable_prime(m):
    if m < 2:
        return False
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41):
        if m % p == 0:
            return m == p
    d, s = m - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for a in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41):
        x = pow(a, d, m)
        if x in (1, m - 1):
            continue
        for _ in range(s - 1):
            x = x * x % m
            if x == m - 1:
                break
        else:
            return False
    return True


def factorial_mod(n, q):
    """n! mod prime q for q > n, via (q-1)! = -1."""
    tail = 1
    for m in range(n + 1, q):
        tail = tail * m % q
    return (-pow(tail, -1, q)) % q


def check(n):
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        return 1, "bad candidate value %r" % (n,)
    if n <= 3000:
        v = math.factorial(n) + 1
        r = math.isqrt(v)
        if r * r == v:
            return 0, "EXACT: %d! + 1 = %d^2" % (n, r)
        return 1, "%d! + 1 is not a perfect square (exact check)" % n
    q = n + 2001
    tested = 0
    while tested < 64:
        q += 1
        if not is_probable_prime(q):
            continue
        r = (factorial_mod(n, q) + 1) % q
        if r != 0 and pow(r, (q - 1) // 2, q) != 1:
            return 1, "n! + 1 is not a square modulo the prime %d" % q
        tested += 1
    return 0, ("n! + 1 is a square modulo 64 independent primes above n; "
               "very strong evidence, not a proof - needs expert review")


if __name__ == "__main__":
    try:
        cand = json.load(open(sys.argv[1]))
        n = cand["data"]["n"]
    except Exception as e:
        print("REJECTED: unreadable candidate: %s" % e)
        sys.exit(1)
    code, msg = check(n)
    print(("VERIFIED: " if code == 0 else "REJECTED: ") + msg)
    sys.exit(code)
