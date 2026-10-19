"""Optional: push a small status snapshot to GitHub for GitHub Pages.

Off by default. When switched on it builds ONE commit that changes only
``docs/status/*.json``, on top of the remote branch, without touching your
checkout, your current branch or any of your own unpushed commits (it uses
a private git index and ``git commit-tree``). At most once an hour, never
more than 1 MB, never logs or checkpoints. Candidate details are left out
of the public copy; only their status and a short summary are published.
"""

import os
import shutil
import subprocess
import tempfile
import time

from . import atomic, paths

MAX_BYTES = 1_000_000
MIN_INTERVAL_S = 3600


def _git(args, timeout=120, env_extra=None, input_text=None):
    env = dict(os.environ)
    env.setdefault("GIT_AUTHOR_NAME", "mathrun")
    env.setdefault("GIT_AUTHOR_EMAIL", "mathrun@localhost")
    env.setdefault("GIT_COMMITTER_NAME", env["GIT_AUTHOR_NAME"])
    env.setdefault("GIT_COMMITTER_EMAIL", env["GIT_AUTHOR_EMAIL"])
    env["GIT_TERMINAL_PROMPT"] = "0"  # never hang waiting for a password
    if env_extra:
        env.update(env_extra)
    r = subprocess.run(["git"] + args, cwd=paths.REPO, capture_output=True, text=True,
                       timeout=timeout, env=env, input=input_text)
    return r.returncode, (r.stdout + r.stderr).strip(), r.stdout.strip()


def _public(obj):
    """Trim histories and drop anything private or unreviewed from the public copy."""
    if not isinstance(obj, dict):
        return obj
    if isinstance(obj.get("history"), list):
        h = obj["history"]
        if len(h) > 400:
            step = len(h) // 400 + 1
            obj["history"] = h[:-100:step] + h[-100:]
    if "candidates" in obj:
        obj["candidates"] = [{k: c.get(k) for k in ("id", "status", "summary", "kind", "found_at")}
                             for c in obj.get("candidates", [])]
    for key in ("last_error",):
        if isinstance(obj.get(key), str):
            obj[key] = obj[key].replace(paths.REPO, "<mathrun>").replace(os.path.expanduser("~"), "~")
    for p in obj.get("problems", []):
        if isinstance(p.get("last_error"), str):
            p["last_error"] = p["last_error"].replace(paths.REPO, "<mathrun>").replace(
                os.path.expanduser("~"), "~")
    return obj


def stage_snapshot(dest):
    """Write the public copy of the status JSON into folder dest. Returns {name: path}."""
    src = paths.status_dir()
    if not os.path.isdir(src):
        raise RuntimeError("no status files yet - start the runner first")
    os.makedirs(dest, exist_ok=True)
    out, total = {}, 0
    for n in sorted(os.listdir(src)):
        if not n.endswith(".json"):
            continue
        obj = atomic.read_json(os.path.join(src, n))
        if obj is None:
            continue
        path = os.path.join(dest, n)
        atomic.atomic_write_json(path, _public(obj), durable=False)
        total += os.path.getsize(path)
        out[n] = path
    if total > MAX_BYTES:
        raise RuntimeError("snapshot is %d bytes, over the 1 MB limit; not publishing" % total)
    return out, total


def publish(cfg, now=None):
    now = now or time.time()
    stamp = paths.control_file("last_publish")
    last = (atomic.read_json(stamp, {}) or {}).get("t", 0)
    if now - last < MIN_INTERVAL_S - 60:
        return False, "skipped: last publish was %d minutes ago (limit: once an hour)" % (
            (now - last) // 60)
    pub = cfg["publish"]
    remote, branch = pub.get("remote", "origin"), pub.get("branch", "main")
    if not shutil.which("git"):
        return False, "git is not installed"
    work = paths.ensure("publish")
    files, size = stage_snapshot(os.path.join(work, "status"))
    code, out, _ = _git(["fetch", "--quiet", remote, branch])
    if code:
        return False, "git fetch failed: " + out[-300:]
    code, out, base = _git(["rev-parse", "%s/%s" % (remote, branch)])
    if code:
        return False, "cannot find %s/%s: %s" % (remote, branch, out[-200:])
    index = os.path.join(work, "index")
    if os.path.exists(index):
        os.unlink(index)
    env = {"GIT_INDEX_FILE": index}
    code, out, _ = _git(["read-tree", base], env_extra=env)
    if code:
        return False, "git read-tree failed: " + out
    # remove old snapshot files, then add the new ones (only under docs/status/)
    code, out, listing = _git(["ls-files", "docs/status"], env_extra=env)
    for name in listing.splitlines():
        if name.endswith(".json"):
            _git(["update-index", "--force-remove", name], env_extra=env)
    for name, path in files.items():
        code, out, blob = _git(["hash-object", "-w", path])
        if code:
            return False, "git hash-object failed: " + out
        code, out, _ = _git(["update-index", "--add", "--cacheinfo", "100644,%s,docs/status/%s" % (blob, name)],
                            env_extra=env)
        if code:
            return False, "git update-index failed: " + out
    code, out, tree = _git(["write-tree"], env_extra=env)
    if code:
        return False, "git write-tree failed: " + out
    code, out, base_tree = _git(["rev-parse", base + "^{tree}"])
    atomic.atomic_write_json(stamp, {"t": now})
    if tree == base_tree:
        return True, "nothing changed"
    code, out, commit = _git(["commit-tree", tree, "-p", base, "-m", "Dashboard status snapshot"])
    if code:
        return False, "git commit-tree failed: " + out
    code, out, _ = _git(["push", remote, "%s:refs/heads/%s" % (commit, branch)])
    if code:
        return False, "git push failed: " + out[-500:]
    return True, "published %d bytes to %s/%s (your own checkout was not touched)" % (size, remote, branch)
