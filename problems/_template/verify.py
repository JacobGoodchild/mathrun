"""Independent verifier: different code from the searcher, exact arithmetic.
Usage: python3 verify.py candidate.json  -> exit 0 verified, 1 rejected, 2 unsure."""
import json
import sys


def check(n):
    if not isinstance(n, int) or isinstance(n, bool):
        return 1, "bad candidate"
    return 1, "template verifier rejects everything - write the real check"


if __name__ == "__main__":
    try:
        code, msg = check(json.load(open(sys.argv[1]))["data"]["n"])
    except Exception as e:
        code, msg = 1, "unreadable candidate: %r" % (e,)
    print(("VERIFIED: " if code == 0 else "REJECTED: ") + msg)
    sys.exit(code)
