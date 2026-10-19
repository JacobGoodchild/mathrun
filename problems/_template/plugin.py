"""Template plugin. The runner calls these functions."""
import os

START = 1          # first number NOT already covered by published searches
L = 10 ** 9        # numbers per unit


def unit(index, state):
    """Parameters for work unit number `index` (0, 1, 2, ...)."""
    a = START + index * L
    return {"a": a, "b": a + L}


def argv(u, ctx):
    """Command line for one unit. ctx: dir, bin, work (scratch folder), seconds."""
    return [os.path.join(ctx["bin"], "searcher"), str(u["a"]), str(u["b"])]


def parse(u, proto):
    """proto = dict(done=..., cands=[...], bests=[...], notes=[...]). Check it, return result."""
    if int(proto["done"]["cases"]) != u["b"] - u["a"]:
        raise ValueError("wrong count")
    return {"cases": int(proto["done"]["cases"]), "candidates": proto["cands"]}


def frontier(state, ledger):
    """What may honestly be claimed: everything below ledger.frontier is finished."""
    top = START + ledger.frontier * L
    return {"text": "all n < %d checked" % top, "value": top}


# Optional: initial_state(), merge(state, unit, result), exhausted(state, ledger),
# corruptions(candidate) -> damaged copies the verifier must reject.

MINI = [  # short runs for ./mathrun selftest; reproduce something known
    {"name": "small range", "unit": {"a": 1, "b": 1000}, "check": lambda r: None},
]
