"""./mathrun selftest

1. Runs every unit test: core tests in tests/, plus each problem's test_*.py
   (which reproduce known results).
2. Runs a short "mini-run" of every searcher (capped at 30 seconds each, run
   in parallel), checks it reproduces what is expected, and checks that the
   independent verifier ACCEPTS the known-good candidates and REJECTS
   deliberately damaged copies of them.
"""

import concurrent.futures as cf
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

from . import paths, problems

MINI_TIMEOUT_S = 30


def run_unit_tests(verbose=False):
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.discover(os.path.join(paths.REPO, "tests"), top_level_dir=paths.REPO))
    for p in problems.discover(include_toys=True):
        if any(n.startswith("test_") and n.endswith(".py") for n in os.listdir(p.folder)):
            sys.path.insert(0, p.folder)
            try:
                for name in sorted(os.listdir(p.folder)):
                    if name.startswith("test_") and name.endswith(".py"):
                        mod_name = "mrtest_%s_%s" % (p.slug.replace("-", "_"), name[:-3])
                        import importlib.util
                        spec = importlib.util.spec_from_file_location(
                            mod_name, os.path.join(p.folder, name))
                        mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(mod)
                        suite.addTests(loader.loadTestsFromModule(mod))
            finally:
                sys.path.remove(p.folder)
    result = unittest.TextTestRunner(verbosity=2 if verbose else 1).run(suite)
    return result.wasSuccessful()


def run_verifier(p, cand):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(cand, f)
        path = f.name
    try:
        r = subprocess.run([sys.executable, "-I", p.path("verify.py"), path],
                           capture_output=True, text=True, timeout=600, cwd=p.folder)
        return r.returncode, (r.stdout + r.stderr)[-1500:]
    finally:
        os.unlink(path)


def mini_run(p):
    """Returns (ok, message)."""
    t0 = time.time()
    plugin = p.plugin
    minis = getattr(plugin, "MINI", None)
    if not minis:
        return False, "no MINI runs defined"
    if not p.is_built():
        return False, "not built (./mathrun install)"
    notes = []
    for m in minis:
        work = tempfile.mkdtemp(prefix="mathrun-mini-")
        argv = plugin.argv(m["unit"], {"dir": p.folder, "bin": p.path("bin"), "work": work,
                                       "seconds": m.get("seconds", 5)})
        try:
            r = subprocess.run(argv, capture_output=True, text=True, timeout=MINI_TIMEOUT_S,
                               cwd=work)
        except subprocess.TimeoutExpired:
            return False, "mini-run %s took over %ds" % (m.get("name", "?"), MINI_TIMEOUT_S)
        if r.returncode != 0:
            return False, "searcher exited %d: %s" % (r.returncode, r.stderr[-500:])
        proto = problems.parse_protocol(r.stdout)
        if proto["done"] is None:
            return False, "no DONE line"
        result = plugin.parse(m["unit"], proto)
        try:
            m["check"](result)
        except AssertionError as e:
            return False, "mini-run %s: wrong result: %s" % (m.get("name", "?"), e)
        for c in result.get("candidates", [])[:3]:
            cand = {"problem": p.slug, "unit": m["unit"], "kind": c.get("kind"),
                    "summary": c.get("summary"), "data": c.get("data")}
            code, out = run_verifier(p, cand)
            if code != 0:
                return False, "verifier did not accept a known-good candidate: %s" % out
            if hasattr(plugin, "corruptions"):
                for bad in plugin.corruptions(cand):
                    code, out = run_verifier(p, bad)
                    if code != 1:
                        return False, "verifier ACCEPTED a damaged candidate (exit %s): %s" % (
                            code, json.dumps(bad)[:300])
            notes.append("verifier ok")
    return True, "%.1fs %s" % (time.time() - t0, ", ".join(sorted(set(notes))))


def main(args):
    quick = "--quick" in args
    print("== unit tests ==")
    ok = run_unit_tests(verbose="-v" in args)
    if quick:
        return 0 if ok else 1
    print("\n== mini-runs ==")
    probs = problems.discover(include_toys=True)
    workers = max(1, (os.cpu_count() or 2) - 1)
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(mini_run, p): p for p in probs}
        results = {}
        for fut in cf.as_completed(futs):
            p = futs[fut]
            try:
                results[p.slug] = fut.result()
            except Exception as e:
                results[p.slug] = (False, "crashed: %r" % e)
    for slug in sorted(results):
        good, msg = results[slug]
        print("  %-4s %-32s %s" % ("ok" if good else "FAIL", slug, msg))
        ok = ok and good
    print("\nSELFTEST %s" % ("PASSED" if ok else "FAILED"))
    return 0 if ok else 1
