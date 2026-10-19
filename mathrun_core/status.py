"""Small JSON status files that the dashboard reads.

``status/index.json``   machine panel + one summary per problem + alerts
``status/<slug>.json``  everything for a problem's detail page

Kept deliberately small (well under 1 MB in total) so publishing them to
GitHub Pages is cheap.
"""

import os
import time

from . import atomic, ledger, paths

STALE_AFTER_S = 120


def _fmt_rate(x):
    if not x:
        return None
    return float("%.4g" % x)


def problem_summary(p, st, running_jobs=0, paused_jobs=0):
    led = ledger.Ledger(st["ledger"])
    try:
        front = p.plugin.frontier(st["plugin"], led)
    except Exception as e:  # never let one plugin break the dashboard
        front = {"text": "frontier unavailable (%s)" % e}
    cands = st.get("candidates", [])
    verified = [c for c in cands if c.get("status", "").startswith("VERIFIED")]
    open_cands = [c for c in cands if c.get("status", "").startswith(("VERIFIED", "pending"))]
    front = dict(front)
    if st.get("bug"):
        # a rejected candidate means the searcher may be wrong: nothing it claimed is trusted
        front["text"] = "UNTRUSTED until checked (a candidate failed verification): " + \
            str(front.get("text", ""))
        front["untrusted"] = True
    elif open_cands:
        front["text"] = str(front.get("text", "")) + \
            " - except %d candidate(s) under review" % len(open_cands)
    if st.get("bug"):
        state = "paused: possible searcher bug"
    elif st.get("disabled_reason"):
        state = "stopped: " + st["disabled_reason"]
    elif running_jobs:
        state = "running"
    elif paused_jobs:
        state = "paused"
    else:
        state = "queued"
    return {
        "slug": p.slug,
        "name": p.name,
        "category": p.category,
        "summary": p.meta.get("summary", ""),
        "mode": p.mode,
        "state": state,
        "workers": running_jobs,
        "frontier": front,
        "record": p.meta.get("record", ""),
        "cpu_hours": round(st.get("cpu_seconds", 0.0) / 3600.0, 3),
        "units_done": st.get("units_done", 0),
        "cases": st.get("cases", 0),
        "speed_per_cpu_s": _fmt_rate(st.get("speed")),
        "speed_unit": p.meta.get("case_name", "cases"),
        "last_checkpoint": st.get("last_checkpoint"),
        "candidates_total": len(cands),
        "verified": len(verified),
        "best": (st.get("bests") or [None])[-1],
        "last_error": st.get("last_error"),
        "weight": p.weight,
    }


def write_all(runner, stopped=False):
    now = time.time()
    problems_out = []
    alerts = []
    for p in runner.problems:
        st = runner.states[p.slug]
        running = sum(1 for j in runner.jobs if j.problem is p and not j.paused)
        paused = sum(1 for j in runner.jobs if j.problem is p and j.paused)
        s = problem_summary(p, st, running, paused)
        problems_out.append(s)
        hist = atomic.read_json(paths.history_path(p.slug), [])
        cand_full = []
        for c in st.get("candidates", [])[-50:]:
            rec = atomic.read_json(os.path.join(paths.candidates_dir(p.slug), c["id"] + ".json"),
                                   None) or dict(c)
            rec.pop("verifier_output_full", None)
            if isinstance(rec.get("verifier_output"), str):
                rec["verifier_output"] = rec["verifier_output"][-4000:]
            cand_full.append(rec)
            if rec.get("status", "").startswith("VERIFIED"):
                alerts.append({"slug": p.slug, "name": p.name, "id": rec.get("id"),
                               "summary": rec.get("summary"), "found_at": rec.get("found_at")})
        detail = dict(s)
        detail.update({"readme": p.readme(), "history": hist[-1500:], "candidates": cand_full,
                       "bests": st.get("bests", [])[-20:], "notes": st.get("notes", [])[-20:],
                       "bug": st.get("bug"), "meta": {k: v for k, v in p.meta.items()
                                                     if isinstance(v, (str, int, float))}})
        atomic.atomic_write_json(os.path.join(paths.status_dir(), p.slug + ".json"), detail,
                                 durable=False)
    d = runner.decision
    machine = {
        "state": "stopped" if stopped else ("running" if d.get("running") else "paused"),
        "reason": d.get("reason"),
        "temp_c": d.get("temp_c"),
        "workers_allowed": d.get("workers", 0),
        "workers_max": runner.max_workers,
        "workers_busy": sum(1 for j in runner.jobs if not j.paused),
        "disk_mb": round((d.get("disk_bytes") or 0) / 1e6, 1),
        "disk_cap_gb": runner.cfg["machine"]["disk_cap_gb"],
        "runner_started": runner.started_at,
    }
    index = {"generated": now, "stale_after_s": STALE_AFTER_S, "machine": machine,
             "problems": problems_out, "alerts": alerts}
    atomic.atomic_write_json(os.path.join(paths.status_dir(), "index.json"), index,
                             durable=False)
    return index
