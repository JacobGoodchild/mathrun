"""Independent check for the toy problem (exact Python integers)."""
import json
import sys


def check(n):
    return isinstance(n, int) and 0 <= n < 2**32 and (n * 2654435761) % 2**32 == 0xDEADBEEF


if __name__ == "__main__":
    cand = json.load(open(sys.argv[1]))
    n = cand.get("data", {}).get("n")
    if check(n):
        print("VERIFIED: n=%d satisfies the toy equation" % n)
        sys.exit(0)
    print("REJECTED: n=%r does not satisfy the toy equation" % (n,))
    sys.exit(1)
