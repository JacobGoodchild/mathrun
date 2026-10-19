"""Problem plugins.

Each problem lives in ``problems/<slug>/`` with:

* ``problem.toml``  - name, category, weight, unit length, etc.
* ``plugin.py``     - turns a unit number into a searcher command line and
                       reads the searcher's output (see ADDING_A_PROBLEM.md)
* ``verify.py``     - the independent verifier (separate code, exact maths)
* ``Makefile``      - builds the C searcher into ``bin/``
* ``README.md``     - the problem in plain English, sources, honest odds
* ``test_*.py``     - tests that reproduce known results
"""

import importlib.util
import json
import os
import sys

from . import paths, tomlmini

REQUIRED_FUNCS = ("unit", "argv", "parse", "frontier")


class Problem:
    def __init__(self, folder):
        self.folder = folder
        self.slug = os.path.basename(folder)
        self.meta = tomlmini.load_file(os.path.join(folder, "problem.toml"))
        self.name = self.meta.get("name", self.slug)
        self.category = self.meta.get("category", "Other")
        self.weight = float(self.meta.get("weight", 1.0))
        self.mode = self.meta.get("mode", "range")  # "range" or "search"
        self.max_parallel = int(self.meta.get("max_parallel", 64))
        self.unit_seconds = float(self.meta.get("unit_seconds", 180))
        self.toy = bool(self.meta.get("toy", False))
        self._plugin = None

    @property
    def plugin(self):
        if self._plugin is None:
            path = os.path.join(self.folder, "plugin.py")
            name = "mathrun_plugin_" + self.slug.replace("-", "_")
            spec = importlib.util.spec_from_file_location(name, path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[name] = mod
            spec.loader.exec_module(mod)
            for f in REQUIRED_FUNCS:
                if not hasattr(mod, f):
                    raise RuntimeError("%s/plugin.py is missing %s()" % (self.slug, f))
            self._plugin = mod
        return self._plugin

    def path(self, *parts):
        return os.path.join(self.folder, *parts)

    def is_built(self):
        binaries = self.meta.get("binaries", [])
        return all(os.path.exists(self.path("bin", b)) for b in binaries)

    def readme(self):
        try:
            with open(self.path("README.md"), encoding="utf-8") as f:
                return f.read()
        except OSError:
            return ""

    def initial_state(self):
        if hasattr(self.plugin, "initial_state"):
            return self.plugin.initial_state()
        return {}

    def __repr__(self):
        return "Problem(%s)" % self.slug


def discover(include_toys=False, root=None):
    root = root or paths.PROBLEMS
    out = []
    if not os.path.isdir(root):
        return out
    for name in sorted(os.listdir(root)):
        folder = os.path.join(root, name)
        if name.startswith(("_", ".")) or not os.path.isfile(os.path.join(folder, "problem.toml")):
            continue
        p = Problem(folder)
        if p.toy and not include_toys:
            continue
        out.append(p)
    return out


def selected(cfg, include_toys=False):
    only = set(cfg["problems"].get("only") or [])
    skip = set(cfg["problems"].get("skip") or [])
    weights = cfg["problems"].get("weights") or {}
    out = []
    for p in discover(include_toys=include_toys or bool(only)):
        if only and p.slug not in only:
            continue
        if p.slug in skip:
            continue
        if p.slug in weights:
            p.weight = float(weights[p.slug])
        out.append(p)
    return out


def parse_protocol(text):
    """Read the line protocol every searcher speaks on stdout.

    ``CAND {json}``  a candidate (saved and independently verified)
    ``BEST {json}``  a new personal best for search-type problems
    ``NOTE {json}``  something worth keeping that is not a candidate
    ``DONE {json}``  the unit finished; must be the last protocol line

    Returns dict(done=dict or None, cands=[...], bests=[...], notes=[...]).
    A unit without a DONE line did not finish and is never counted.
    """
    res = {"done": None, "cands": [], "bests": [], "notes": []}
    for line in text.splitlines():
        tag, _, rest = line.partition(" ")
        if tag not in ("CAND", "BEST", "NOTE", "DONE"):
            continue
        try:
            obj = json.loads(rest)
        except ValueError:
            raise ValueError("searcher printed malformed %s line: %r" % (tag, line[:200]))
        if tag == "DONE":
            if res["done"] is not None:
                raise ValueError("searcher printed two DONE lines")
            res["done"] = obj
        elif res["done"] is not None:
            raise ValueError("searcher printed %s after DONE" % tag)
        else:
            res[{"CAND": "cands", "BEST": "bests", "NOTE": "notes"}[tag]].append(obj)
    return res
