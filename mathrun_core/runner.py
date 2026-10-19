"""The long-lived background process that hands out work and keeps records.

Main loop, about once a second:

1. Ask the guards how many searchers may run (heat, idle, gaming, disk).
2. Pause (SIGSTOP) or resume (SIGCONT) running searchers to match.
3. Start new work units on free cores, sharing CPU between problems by weight.
4. Collect finished units: count them, save checkpoints (atomically), pass
   any candidates to the independent verifier.
5. Every so often write status files for the dashboard and history points.

Stopping (``mathrun stop``, Ctrl-C or a system shutdown) kills the running
units and saves. Unfinished units are simply redone next time, so at most a
few minutes of work are lost and no checkpoint can be half-written.
"""

import fcntl
import logging
import logging.handlers
import os
import shutil
import signal
import subprocess
import sys
import threading
import time

from . import alerts, atomic, config, guards, ledger, paths, problems, status

log = logging.getLogger("mathrun")

STATE_VERSION = 1
HISTORY_EVERY_S = 300
STATUS_EVERY_S = 20
GUARD_EVERY_S = 5
MAX_FAILS_IN_A_ROW = 8
MAX_FAILS_SAME_UNIT = 5
MAX_CANDS_PER_UNIT = 25
VERIFY_TIMEOUT_S = 1800
KEEP_FAILED_OUTPUTS = 5


def setup_logging(to_stderr=False):
    os.makedirs(paths.logs_dir(), exist_ok=True)
    log.setLevel(logging.INFO)
    for h in list(log.handlers):
        log.removeHandler(h)
    h = logging.handlers.RotatingFileHandler(os.path.join(paths.logs_dir(), "runner.log"),
                                             maxBytes=5_000_000, backupCount=3)
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(h)
    if to_stderr:
        s = logging.StreamHandler(sys.stderr)
        s.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        log.addHandler(s)


def lowprio(nice):
    def fn():
        try:
            os.nice(nice)
        except OSError:
            pass
    return fn


def ionice_prefix():
    return ["ionice", "-c", "3"] if shutil.which("ionice") else []


def fresh_state(problem):
    return {
        "version": STATE_VERSION,
        "slug": problem.slug,
        "ledger": ledger.Ledger().to_dict(),
        "plugin": problem.initial_state(),
        "cpu_seconds": 0.0,
        "units_done": 0,
        "cases": 0,
        "failures_in_a_row": 0,
        "failures_total": 0,
        "backoff_until": 0.0,
        "disabled_reason": None,
        "bug": None,
        "candidates": [],
        "bests": [],
        "notes": [],
        "first_started": time.time(),
        "last_checkpoint": None,
        "speed": None,
    }


def load_state(problem):
    st = atomic.read_json(paths.state_path(problem.slug))
    if not isinstance(st, dict) or st.get("version") != STATE_VERSION:
        return fresh_state(problem)
    base = fresh_state(problem)
    base.update(st)
    return base


def save_state(problem, st):
    st["last_checkpoint"] = time.time()
    atomic.atomic_write_json(paths.state_path(problem.slug), st)


def append_history(problem, st, front):
    path = paths.history_path(problem.slug)
    hist = atomic.read_json(path, [])
    if not isinstance(hist, list):
        hist = []
    hist.append({"t": round(time.time()), "f": front.get("value"), "cases": st["cases"],
                 "cpu": round(st["cpu_seconds"], 1), "units": st["units_done"]})
    if len(hist) > 3000:  # keep the file small: thin out the oldest half
        half = len(hist) // 2
        hist = hist[:half:2] + hist[half:]
    atomic.atomic_write_json(path, hist, durable=False)


class Job:
    def __init__(self, problem, index, unit, proc, out_path, err_path):
        self.problem = problem
        self.index = index
        self.unit = unit
        self.proc = proc
        self.out_path = out_path
        self.err_path = err_path
        self.started = time.monotonic()
        self.active_s = 0.0  # time spent not paused
        self.last_tick = self.started
        self.paused = False


class VerifyJob:
    def __init__(self, problem, cand_path, proc, out_path):
        self.problem = problem
        self.cand_path = cand_path
        self.proc = proc
        self.out_path = out_path
        self.started = time.monotonic()


class Runner:
    def __init__(self, cfg=None, include_toys=False, max_units=None, problem_list=None):
        self.cfg = cfg or config.load()
        self.max_workers = config.worker_count(self.cfg)
        self.guards = guards.Guards(self.cfg, self.max_workers)
        self.problems = problem_list if problem_list is not None else \
            problems.selected(self.cfg, include_toys=include_toys)
        self.states = {}
        self.jobs = []
        self.verifies = []
        self.stop_flag = False
        self.max_units = max_units  # for tests: stop after this many units
        self.units_this_session = 0
        self.session_cpu = {}
        self.decision = {"workers": 0, "running": False, "reason": "starting"}
        self.last_guard = -1e9
        self.last_status = -1e9
        self.last_history = {}
        self.last_publish = time.monotonic()
        self.publishing = None
        self.nice = int(self.cfg["machine"]["nice"])
        self.started_at = time.time()

    # ---------- lifecycle ----------
    def request_stop(self, *_):
        self.stop_flag = True

    def run(self):
        for d in ("state", "status", "logs", "work", "candidates", "control"):
            paths.ensure(d)
        lock = open(paths.lock_file(), "w")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            log.error("another mathrun runner is already going; exiting")
            return 1
        atomic.atomic_write_text(paths.pid_file(), str(os.getpid()))
        signal.signal(signal.SIGTERM, self.request_stop)
        signal.signal(signal.SIGINT, self.request_stop)
        signal.signal(signal.SIGHUP, self.request_stop)
        try:
            os.nice(self.nice)
        except OSError:
            pass
        usable = []
        for p in self.problems:
            if not p.is_built():
                log.warning("%s is not built (run ./mathrun install); skipping", p.slug)
                continue
            try:
                p.plugin
            except Exception as e:
                log.error("%s plugin failed to load: %s", p.slug, e)
                continue
            usable.append(p)
            self.states[p.slug] = load_state(p)
            self.session_cpu[p.slug] = 0.0
        self.problems = usable
        log.info("runner started: %d problems, up to %d workers", len(usable), self.max_workers)
        # Candidates whose verification was interrupted last time get re-checked.
        for p in usable:
            for c in self.states[p.slug]["candidates"]:
                if c.get("status") == "pending verification":
                    path = os.path.join(paths.candidates_dir(p.slug), c["id"] + ".json")
                    if os.path.exists(path):
                        self._start_verify(p, path)
        try:
            while not self.stop_flag:
                self.tick()
                if self.max_units is not None and self.units_this_session >= self.max_units \
                        and not self.jobs and not self.verifies:
                    break
                time.sleep(0.2 if self.max_units is not None else 1.0)
        finally:
            self.shutdown()
            try:
                os.unlink(paths.pid_file())
            except OSError:
                pass
            lock.close()
        return 0

    def shutdown(self):
        for j in self.jobs:
            self._kill(j.proc)
        for v in self.verifies:
            self._kill(v.proc)
        for j in self.jobs:
            self._reap(j.proc, block=True)
            self._cleanup_files(j, keep=False)
        for v in self.verifies:
            self._reap(v.proc, block=True)
        self.jobs = []
        self.verifies = []  # pending candidates are re-verified on next start
        for p in self.problems:
            save_state(p, self.states[p.slug])
        self.decision = {"workers": 0, "running": False, "reason": "stopped"}
        self.write_status(stopped=True)
        log.info("runner stopped cleanly")

    # ---------- main loop ----------
    def tick(self):
        now = time.monotonic()
        if now - self.last_guard >= GUARD_EVERY_S:
            self.last_guard = now
            old = self.decision.get("reason")
            self.decision = self.guards.evaluate()
            if self.decision.get("reason") != old:
                log.info("guards: %s", self.decision.get("reason"))
                self.last_status = -1e9  # show the change on the dashboard straight away
        self._apply_pause()
        self._collect()
        self._collect_verifies()
        self._start_jobs()
        if now - self.last_status >= STATUS_EVERY_S:
            self.last_status = now
            self.write_status()
        self._maybe_publish(now)

    def _apply_pause(self):
        allowed = self.decision["workers"]
        now = time.monotonic()
        for k, j in enumerate(self.jobs):
            if not j.paused:
                j.active_s += now - j.last_tick
            j.last_tick = now
            want_paused = k >= allowed
            if want_paused != j.paused:
                try:
                    os.killpg(j.proc.pid, signal.SIGSTOP if want_paused else signal.SIGCONT)
                    j.paused = want_paused
                except OSError:
                    pass

    def _eligible(self):
        now = time.time()
        out = []
        for p in self.problems:
            st = self.states[p.slug]
            if st.get("disabled_reason") or st.get("bug"):
                continue
            if st.get("backoff_until", 0) > now:
                continue
            if sum(1 for j in self.jobs if j.problem is p) >= p.max_parallel:
                continue
            if hasattr(p.plugin, "exhausted"):
                try:
                    if p.plugin.exhausted(st["plugin"], ledger.Ledger(st["ledger"])):
                        continue
                except Exception as e:  # a plugin bug must never take the runner down
                    log.exception("%s: exhausted() failed", p.slug)
                    self._fail(p, "plugin error in exhausted(): %s" % e)
                    continue
            out.append(p)
        return out

    def _start_jobs(self):
        if self.stop_flag:
            return
        if self.max_units is not None and \
                self.units_this_session + len(self.jobs) >= self.max_units:
            return
        while len(self.jobs) < self.decision["workers"]:
            cands = self._eligible()
            if not cands:
                return

            def load(p):
                running = sum(p.unit_seconds for j in self.jobs if j.problem is p)
                return (self.session_cpu[p.slug] + running) / max(p.weight, 1e-6)

            p = min(cands, key=load)
            if not self._launch(p):
                return
            if self.max_units is not None and \
                    self.units_this_session + len(self.jobs) >= self.max_units:
                return

    def _launch(self, p):
        st = self.states[p.slug]
        led = ledger.Ledger(st["ledger"])
        inflight = {j.index for j in self.jobs if j.problem is p}
        index = led.issue(inflight)
        st["ledger"] = led.to_dict()
        try:
            unit = p.plugin.unit(index, st["plugin"])
            wd = paths.ensure("work", p.slug)
            argv = p.plugin.argv(unit, {"dir": p.folder, "bin": p.path("bin"),
                                        "work": wd, "seconds": p.unit_seconds})
        except Exception as e:
            log.exception("%s: could not build unit %d", p.slug, index)
            self._fail(p, "plugin error building unit: %s" % e)
            return False
        out_path = os.path.join(wd, "u%d.out" % index)
        err_path = os.path.join(wd, "u%d.err" % index)
        try:
            with open(out_path, "w") as fo, open(err_path, "w") as fe:
                proc = subprocess.Popen(ionice_prefix() + list(argv), stdout=fo, stderr=fe,
                                        stdin=subprocess.DEVNULL, cwd=wd,
                                        preexec_fn=lowprio(self.nice), start_new_session=True)
        except OSError as e:
            self._fail(p, "could not start searcher: %s" % e)
            return False
        self.jobs.append(Job(p, index, unit, proc, out_path, err_path))
        return True

    @staticmethod
    def _kill(proc):
        try:
            os.killpg(proc.pid, signal.SIGCONT)
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            pass

    @staticmethod
    def _reap(proc, block=False):
        """Return (finished, exit_code, cpu_seconds) using wait4 for CPU usage."""
        if proc.returncode is not None:
            return True, proc.returncode, 0.0
        try:
            pid, status_, ru = os.wait4(proc.pid, 0 if block else os.WNOHANG)
        except ChildProcessError:
            proc.returncode = -1
            return True, -1, 0.0
        if pid == 0:
            return False, None, 0.0
        code = os.waitstatus_to_exitcode(status_) if hasattr(os, "waitstatus_to_exitcode") \
            else (status_ >> 8 if os.WIFEXITED(status_) else -os.WTERMSIG(status_))
        proc.returncode = code
        return True, code, ru.ru_utime + ru.ru_stime

    def _collect(self):
        still = []
        for j in self.jobs:
            done, code, cpu = self._reap(j.proc)
            if not done:
                limit = max(j.problem.unit_seconds * 8, 1800)
                if j.active_s > limit:
                    log.warning("%s unit %d ran too long; killing", j.problem.slug, j.index)
                    self._kill(j.proc)
                    self._reap(j.proc, block=True)
                    self._fail(j.problem, "unit %d timed out" % j.index, j.index)
                    self._cleanup_files(j, keep=True)
                    continue
                still.append(j)
                continue
            self._finish(j, code, cpu)
        self.jobs = still

    def _cleanup_files(self, j, keep):
        if keep:
            fails = paths.ensure("work", j.problem.slug, "failed")
            for src in (j.out_path, j.err_path):
                try:
                    os.replace(src, os.path.join(fails, os.path.basename(src)))
                except OSError:
                    pass
            old = sorted((os.path.join(fails, f) for f in os.listdir(fails)),
                         key=lambda f: os.path.getmtime(f))
            for f in old[:-2 * KEEP_FAILED_OUTPUTS]:
                try:
                    os.unlink(f)
                except OSError:
                    pass
            return
        for src in (j.out_path, j.err_path):
            try:
                os.unlink(src)
            except OSError:
                pass

    def _rescue_candidates(self, j):
        """A failed unit is not counted, but any CAND lines it printed are still saved
        and verified: a real find must never be lost because something else went wrong."""
        try:
            with open(j.out_path, encoding="utf-8", errors="replace") as f:
                lines = f.read().splitlines()
        except OSError:
            return
        import json
        found = 0
        for line in lines:
            if not line.startswith("CAND ") or found >= MAX_CANDS_PER_UNIT:
                continue
            try:
                c = json.loads(line[5:])
            except ValueError:
                continue
            if isinstance(c, dict):
                found += 1
                self._new_candidate(j.problem, j, c)

    def _fail(self, p, why, index=None):
        st = self.states[p.slug]
        if index is not None:
            # the same unit failing again and again (while others succeed) must not loop forever
            uf = st.setdefault("unit_failures", {})
            uf[str(index)] = uf.get(str(index), 0) + 1
            if uf[str(index)] >= MAX_FAILS_SAME_UNIT:
                st["disabled_reason"] = "unit %d failed %d times: %s" % (index, uf[str(index)], why)
        st["failures_in_a_row"] += 1
        st["failures_total"] += 1
        delay = min(3600, 15 * 2 ** min(st["failures_in_a_row"], 10))
        st["backoff_until"] = time.time() + delay
        st["last_error"] = why
        log.warning("%s: %s (failure %d in a row, retry in %ds)", p.slug, why,
                    st["failures_in_a_row"], delay)
        if st["failures_in_a_row"] >= MAX_FAILS_IN_A_ROW:
            st["disabled_reason"] = "stopped after %d failures in a row: %s" % (
                st["failures_in_a_row"], why)
            log.error("%s disabled: %s", p.slug, st["disabled_reason"])
        save_state(p, st)

    def _finish(self, j, code, cpu):
        p, st = j.problem, self.states[j.problem.slug]
        self.session_cpu[p.slug] += cpu
        st["cpu_seconds"] += cpu
        if code != 0:
            self._rescue_candidates(j)
            self._fail(p, "searcher exited with code %s on unit %d" % (code, j.index), j.index)
            self._cleanup_files(j, keep=True)
            return
        try:
            with open(j.out_path, encoding="utf-8", errors="replace") as f:
                text = f.read()
            proto = problems.parse_protocol(text)
            if proto["done"] is None:
                raise ValueError("no DONE line")
            if len(proto["cands"]) > MAX_CANDS_PER_UNIT:
                raise ValueError("%d candidates in one unit - surely a bug" % len(proto["cands"]))
            result = p.plugin.parse(j.unit, proto)
        except Exception as e:
            self._rescue_candidates(j)
            self._fail(p, "bad output from unit %d: %s" % (j.index, e), j.index)
            self._cleanup_files(j, keep=True)
            return
        # Candidates are written to disk before anything else happens.
        for c in result.get("candidates", []):
            self._new_candidate(p, j, c)
        led = ledger.Ledger(st["ledger"])
        led.complete(j.index)
        st["ledger"] = led.to_dict()
        uf = st.get("unit_failures")
        if uf:  # forget failure counts of units that are now finished
            st["unit_failures"] = {k: v for k, v in uf.items() if int(k) >= led.frontier and int(k) != j.index}
        if hasattr(p.plugin, "merge"):
            try:
                p.plugin.merge(st["plugin"], j.unit, result)
            except Exception as e:
                log.exception("%s: merge() failed (unit still counted)", p.slug)
                st["merge_error"] = "merge() failed on unit %d: %s" % (j.index, e)
        for b in result.get("bests", []):
            st["bests"] = (st["bests"] + [dict(b, t=round(time.time()))])[-20:]
        for n in result.get("notes", []):
            st["notes"] = (st["notes"] + [dict(n, t=round(time.time()))])[-50:]
        cases = int(result.get("cases", 0))
        st["cases"] += cases
        st["units_done"] += 1
        st["failures_in_a_row"] = 0
        st["last_error"] = st.pop("merge_error", None)
        if cpu > 0 and cases > 0:
            rate = cases / cpu
            st["speed"] = rate if not st.get("speed") else 0.8 * st["speed"] + 0.2 * rate
        save_state(p, st)
        self.units_this_session += 1
        self._cleanup_files(j, keep=False)
        now = time.monotonic()
        if now - self.last_history.get(p.slug, -1e9) >= HISTORY_EVERY_S or self.max_units:
            self.last_history[p.slug] = now
            try:
                append_history(p, st, p.plugin.frontier(st["plugin"], led))
            except Exception:
                log.exception("%s: could not record history", p.slug)

    # ---------- candidate pipeline ----------
    def _new_candidate(self, p, j, c):
        folder = paths.ensure("candidates", p.slug)
        cid = time.strftime("%Y%m%d-%H%M%S") + "-u%d-%d" % (j.index, len(os.listdir(folder)))
        rec = {"id": cid, "problem": p.slug, "problem_name": p.name, "unit": j.unit,
               "unit_index": j.index, "found_at": time.time(), "kind": c.get("kind", "solution"),
               "summary": c.get("summary", ""), "data": c.get("data", {}),
               "status": "pending verification"}
        path = os.path.join(folder, cid + ".json")
        atomic.atomic_write_json(path, rec, indent=1)
        st = self.states[p.slug]
        st["candidates"].append({"id": cid, "status": rec["status"], "summary": rec["summary"],
                                 "kind": rec["kind"], "found_at": rec["found_at"]})
        log.warning("%s: candidate %s saved, sending to independent verifier", p.slug, cid)
        save_state(p, st)
        self._start_verify(p, path)

    def _start_verify(self, p, cand_path):
        out_path = cand_path + ".verify.txt"
        with open(out_path, "w") as fo:
            proc = subprocess.Popen([sys.executable, "-I", p.path("verify.py"), cand_path],
                                    stdout=fo, stderr=subprocess.STDOUT,
                                    stdin=subprocess.DEVNULL, cwd=p.folder,
                                    preexec_fn=lowprio(self.nice), start_new_session=True)
        self.verifies.append(VerifyJob(p, cand_path, proc, out_path))

    def _collect_verifies(self):
        still = []
        for v in self.verifies:
            done, code, _ = self._reap(v.proc)
            if not done and time.monotonic() - v.started > VERIFY_TIMEOUT_S:
                self._kill(v.proc)
                self._reap(v.proc, block=True)
                done, code = True, "timeout"
            if not done:
                still.append(v)
                continue
            self._verdict(v, code)
        self.verifies = still

    def _verdict(self, v, code):
        p, st = v.problem, self.states[v.problem.slug]
        try:
            with open(v.out_path, encoding="utf-8", errors="replace") as f:
                output = f.read()[-20000:]
        except OSError:
            output = ""
        rec = atomic.read_json(v.cand_path, {})
        if code == 0:
            rec["status"] = "VERIFIED CANDIDATE - needs human review"
        elif code == 1:
            rec["status"] = "rejected by verifier (searcher bug)"
        else:
            rec["status"] = "verifier error (needs a look)"
        rec["verifier_output"] = output
        rec["verified_at"] = time.time()
        atomic.atomic_write_json(v.cand_path, rec, indent=1)
        for c in st["candidates"]:
            if c["id"] == rec.get("id"):
                c["status"] = rec["status"]
        if code == 0:
            log.warning("%s: candidate %s VERIFIED by independent check", p.slug, rec.get("id"))
            sent = alerts.send_verified(self.cfg, p.name)
            log.info("alerts sent: %s", sent or "none configured")
        else:
            st["bug"] = {"candidate": rec.get("id"), "status": rec["status"],
                         "at": time.time()}
            log.error("%s: candidate %s %s; problem paused until checked "
                      "(./mathrun clear-bug %s)", p.slug, rec.get("id"), rec["status"], p.slug)
        save_state(p, st)
        self.write_status()

    # ---------- status + publishing ----------
    def write_status(self, stopped=False):
        try:
            status.write_all(self, stopped=stopped)
        except Exception:
            log.exception("could not write status files")

    def _maybe_publish(self, now):
        pub = self.cfg["publish"]
        if not pub.get("enabled") or self.stop_flag:
            return
        if self.publishing is not None and self.publishing.is_alive():
            return
        if now - self.last_publish < 60 * int(pub["interval_minutes"]):
            return
        self.last_publish = now
        from . import publish

        def go():
            try:
                ok, msg = publish.publish(self.cfg)
                log.info("publish: %s", msg)
            except Exception:
                log.exception("publish failed")

        self.publishing = threading.Thread(target=go, daemon=True)
        self.publishing.start()


def main(argv=None):
    setup_logging(to_stderr="--foreground" in (argv or []))
    return Runner().run()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
