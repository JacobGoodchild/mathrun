"""Optional: push a small status snapshot to GitHub for GitHub Pages.

Off by default. When switched on it copies the dashboard's JSON files into
``docs/status/``, commits only that folder, and pushes. Never more than once
an hour, never more than 1 MB, never logs or checkpoints.
"""

import os
import shutil
import subprocess
import time

from . import atomic, paths

MAX_BYTES = 1_000_000
MIN_INTERVAL_S = 3600


def _git(args, timeout=120):
    env = dict(os.environ)
    env.setdefault("GIT_AUTHOR_NAME", "mathrun")
    env.setdefault("GIT_AUTHOR_EMAIL", "mathrun@localhost")
    env.setdefault("GIT_COMMITTER_NAME", env["GIT_AUTHOR_NAME"])
    env.setdefault("GIT_COMMITTER_EMAIL", env["GIT_AUTHOR_EMAIL"])
    env["GIT_TERMINAL_PROMPT"] = "0"  # never hang waiting for a password
    r = subprocess.run(["git"] + args, cwd=paths.REPO, capture_output=True, text=True,
                       timeout=timeout, env=env)
    return r.returncode, (r.stdout + r.stderr).strip()


def _shrink(obj):
    """Trim long histories so the snapshot stays small."""
    if isinstance(obj, dict) and isinstance(obj.get("history"), list):
        h = obj["history"]
        if len(h) > 400:
            step = len(h) // 400 + 1
            obj["history"] = h[:-100:step] + h[-100:]
        for c in obj.get("candidates", []):
            if isinstance(c.get("verifier_output"), str):
                c["verifier_output"] = c["verifier_output"][-2000:]
    return obj


def stage_snapshot(dest=None):
    """Copy status JSON into docs/status. Returns total bytes written."""
    src = paths.status_dir()
    dest = dest or os.path.join(paths.DOCS, "status")
    if not os.path.isdir(src):
        raise RuntimeError("no status files yet - start the runner first")
    os.makedirs(dest, exist_ok=True)
    names = sorted(n for n in os.listdir(src) if n.endswith(".json"))
    total = 0
    for n in names:
        obj = _shrink(atomic.read_json(os.path.join(src, n)))
        if obj is None:
            continue
        atomic.atomic_write_json(os.path.join(dest, n), obj, durable=False)
        total += os.path.getsize(os.path.join(dest, n))
    for n in os.listdir(dest):  # drop status files of problems no longer present
        if n.endswith(".json") and n not in names:
            os.unlink(os.path.join(dest, n))
    if total > MAX_BYTES:
        raise RuntimeError("snapshot is %d bytes, over the 1 MB limit; not publishing" % total)
    return total


def publish(cfg, now=None):
    now = now or time.time()
    stamp = paths.control_file("last_publish")
    last = atomic.read_json(stamp, {}).get("t", 0)
    if now - last < MIN_INTERVAL_S - 60:
        return False, "skipped: last publish was %d minutes ago (limit: once an hour)" % (
            (now - last) // 60)
    pub = cfg["publish"]
    remote, branch = pub.get("remote", "origin"), pub.get("branch", "main")
    if not shutil.which("git"):
        return False, "git is not installed"
    size = stage_snapshot()
    code, out = _git(["add", "--", "docs/status"])
    if code:
        return False, "git add failed: " + out
    code, out = _git(["diff", "--cached", "--quiet", "--", "docs/status"])
    if code == 0:
        atomic.atomic_write_json(stamp, {"t": now})
        return True, "nothing changed"
    code, out = _git(["commit", "-m", "Dashboard status snapshot", "--", "docs/status"])
    if code:
        return False, "git commit failed: " + out
    atomic.atomic_write_json(stamp, {"t": now})
    code, out = _git(["push", remote, "HEAD:" + branch])
    if code:
        # Behind the remote? Only rebase automatically if nothing else is changed locally.
        c2, dirty = _git(["status", "--porcelain"])
        if c2 == 0 and not dirty.strip():
            c3, o3 = _git(["pull", "--rebase", remote, branch])
            if c3 == 0:
                code, out = _git(["push", remote, "HEAD:" + branch])
        if code:
            return False, "git push failed (snapshot committed locally): " + out[-500:]
    return True, "published %d bytes to %s/%s" % (size, remote, branch)
