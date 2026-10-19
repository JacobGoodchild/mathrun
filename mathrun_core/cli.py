"""The ./mathrun command."""

import os
import shutil
import signal
import subprocess
import sys
import time

from . import atomic, config, paths, problems, status

USAGE = """mathrun - home-run searches on famous open problems

  ./mathrun install            check tools, build every searcher, make config.local.toml
  ./mathrun selftest [--quick] run all tests and a short mini-run of every searcher
  ./mathrun start              start the background runner
  ./mathrun stop               save and stop everything cleanly
  ./mathrun status             one-screen summary
  ./mathrun dashboard          open the dashboard at http://127.0.0.1:<port>
  ./mathrun publish            push a status snapshot to GitHub (if switched on)
  ./mathrun gaming on|off      pause / resume everything (e.g. while gaming)
  ./mathrun clear-bug <slug>   un-pause a problem after you've looked at a failed verification
  ./mathrun add-autostart      start mathrun automatically when you log in (systemd user service)
  ./mathrun remove-autostart   undo add-autostart
  ./mathrun run                run the runner in this terminal (for debugging)
"""

APT_HINT = "sudo apt install build-essential python3"


def runner_pid():
    try:
        with open(paths.pid_file()) as f:
            pid = int(f.read().strip())
    except (OSError, ValueError):
        return None
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return None
    except PermissionError:
        return pid
    try:
        with open("/proc/%d/cmdline" % pid, "rb") as f:
            if b"mathrun" not in f.read():
                return None
    except OSError:
        pass
    return pid


# ---------------- install ----------------
def gmp_available():
    src = paths.sub("build", "gmptest.c")
    os.makedirs(os.path.dirname(src), exist_ok=True)
    with open(src, "w") as f:
        f.write("#include <gmp.h>\nint main(void){mpz_t a;mpz_init_set_ui(a,7);"
                "mpz_mul(a,a,a);return mpz_cmp_ui(a,49)!=0;}\n")
    exe = src[:-2]
    r = subprocess.run(["gcc", src, "-o", exe, "-lgmp"], capture_output=True)
    return r.returncode == 0 and subprocess.run([exe]).returncode == 0


def write_build_config():
    """common/build/config.mk tells Makefiles whether real GMP is present."""
    use = gmp_available()
    path = os.path.join(paths.REPO, "common", "build", "config.mk")
    if use:
        text = "BIGNUM_CFLAGS = -DMR_HAVE_GMP\nBIGNUM_LIBS = -lgmp\nBIGNUM_SRC =\n"
    else:
        text = ("BIGNUM_CFLAGS = -I$(MR_ROOT)/common/vendor/mini-gmp\nBIGNUM_LIBS =\n"
                "BIGNUM_SRC = $(MR_ROOT)/common/vendor/mini-gmp/mini-gmp.c\n")
    atomic.atomic_write_text(path, text, durable=False)
    return use


def cmd_install(args):
    ok = True
    print("Checking tools...")
    if sys.version_info < (3, 8):
        print("  python3 is too old (need 3.8+)")
        ok = False
    for tool in ("gcc", "make"):
        if not shutil.which(tool):
            print("  missing: %s" % tool)
            ok = False
    if not ok:
        print("\nPlease run this once, then try again:\n\n    %s\n" % APT_HINT)
        return 1
    print("  python3 %d.%d, gcc and make found" % sys.version_info[:2])
    gmp = write_build_config()
    print("  big numbers: %s" % ("GMP (fast)" if gmp else
                                 "built-in mini-gmp (slower; for speed: sudo apt install libgmp-dev)"))
    for d in ("state", "status", "logs", "work", "candidates", "control"):
        paths.ensure(d)
    local = config.local_path()
    if not os.path.exists(local):
        shutil.copy(os.path.join(paths.REPO, "config.example.toml"), local)
        print("  created config.local.toml (edit it to change settings)")
    failed = []
    for p in problems.discover(include_toys=True):
        if not os.path.exists(p.path("Makefile")):
            continue
        print("Building %s..." % p.slug)
        r = subprocess.run(["make", "-s", "-C", p.folder, "MR_ROOT=" + paths.REPO],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stdout[-2000:] + r.stderr[-2000:])
            failed.append(p.slug)
    if failed:
        print("\nBuild FAILED for: %s" % ", ".join(failed))
        return 1
    print("\nAll built. Next: ./mathrun selftest, then ./mathrun start")
    return 0


# ---------------- start / stop / status ----------------
def cmd_start(args):
    pid = runner_pid()
    if pid:
        print("mathrun is already running (pid %d)." % pid)
        return 0
    missing = [p.slug for p in problems.selected(config.load()) if not p.is_built()]
    if missing:
        print("Not built yet: %s\nRun ./mathrun install first." % ", ".join(missing))
        return 1
    paths.ensure("logs")
    out = open(os.path.join(paths.logs_dir(), "runner.stdout"), "a")
    proc = subprocess.Popen([sys.executable, "-m", "mathrun_core.runner"], cwd=paths.REPO,
                            stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                            start_new_session=True)
    for _ in range(50):
        time.sleep(0.1)
        if runner_pid():
            break
        if proc.poll() is not None:
            print("Runner failed to start; see data/logs/runner.log")
            return 1
    print("mathrun started (pid %d). Dashboard: ./mathrun dashboard" % proc.pid)
    return 0


def cmd_stop(args):
    pid = runner_pid()
    if not pid:
        print("mathrun is not running.")
        return 0
    os.kill(pid, signal.SIGTERM)
    for _ in range(300):
        time.sleep(0.1)
        if not runner_pid():
            print("mathrun stopped; progress saved.")
            return 0
    print("Runner is taking a long time to stop (pid %d)." % pid)
    return 1


def _ago(t):
    if not t:
        return "never"
    s = max(0, time.time() - t)
    if s < 120:
        return "%ds ago" % s
    if s < 7200:
        return "%dm ago" % (s // 60)
    return "%.1fh ago" % (s / 3600)


def cmd_status(args):
    pid = runner_pid()
    idx = atomic.read_json(os.path.join(paths.status_dir(), "index.json"))
    print("Runner: %s" % ("running (pid %d)" % pid if pid else "stopped"))
    if os.path.exists(paths.control_file("gaming")):
        print("Gaming mode: ON (./mathrun gaming off)")
    if not idx:
        print("No status yet.")
        return 0
    m = idx["machine"]
    print("Machine: %s - %s | temp %s | busy %s/%s | data %s MB" % (
        m["state"] if pid else "stopped", m.get("reason"),
        "%.0fC" % m["temp_c"] if m.get("temp_c") else "n/a",
        m.get("workers_busy"), m.get("workers_max"), m.get("disk_mb")))
    for a in idx.get("alerts", []):
        print("!!! VERIFIED CANDIDATE - needs human review: %s (%s)" % (a["name"], a["id"]))
    print()
    for p in idx["problems"]:
        print("%-34s %-10s %s" % (p["name"][:34], p["state"][:10],
                                  (p["frontier"] or {}).get("text", "")))
        print("%-34s cpu %.2f h | units %d | checkpoint %s" % (
            "", p["cpu_hours"], p["units_done"], _ago(p["last_checkpoint"])))
    return 0


def cmd_gaming(args):
    flag = paths.control_file("gaming")
    if not args or args[0] not in ("on", "off"):
        print("Gaming mode is %s. Use: ./mathrun gaming on|off" %
              ("ON" if os.path.exists(flag) else "off"))
        return 0
    if args[0] == "on":
        paths.ensure("control")
        atomic.atomic_write_text(flag, "on\n")
        print("Gaming mode ON: searchers pause within a few seconds.")
    else:
        if os.path.exists(flag):
            os.unlink(flag)
        print("Gaming mode off: searchers resume within a few seconds.")
    return 0


def cmd_clear_bug(args):
    if not args:
        print("Usage: ./mathrun clear-bug <slug>")
        return 1
    if runner_pid():
        print("Please ./mathrun stop first, then clear, then start again.")
        return 1
    st = atomic.read_json(paths.state_path(args[0]))
    if not st:
        print("No state for %s" % args[0])
        return 1
    st["bug"] = None
    st["disabled_reason"] = None
    st["failures_in_a_row"] = 0
    st["backoff_until"] = 0
    atomic.atomic_write_json(paths.state_path(args[0]), st)
    print("Cleared. %s will run again on next start." % args[0])
    return 0


def cmd_dashboard(args):
    from . import dashboard
    cfg = config.load()
    if not runner_pid() and not os.path.exists(os.path.join(paths.status_dir(), "index.json")):
        print("(The runner hasn't written any status yet; the dashboard will be empty.)")
    dashboard.serve(cfg["dashboard"]["port"], open_browser="--no-browser" not in args)
    return 0


def cmd_publish(args):
    from . import publish
    cfg = config.load()
    if not cfg["publish"].get("enabled"):
        print("Publishing is off. Set enabled = true under [publish] in config.local.toml.")
        return 1
    ok, msg = publish.publish(cfg)
    print(msg)
    return 0 if ok else 1


def cmd_run(args):
    from . import runner
    return runner.main(["--foreground"])


def cmd_selftest(args):
    from . import selftest
    return selftest.main(args)


def cmd_autostart(args, add):
    from . import autostart
    return autostart.add() if add else autostart.remove()


COMMANDS = {
    "install": cmd_install,
    "start": cmd_start,
    "stop": cmd_stop,
    "status": cmd_status,
    "dashboard": cmd_dashboard,
    "publish": cmd_publish,
    "selftest": cmd_selftest,
    "gaming": cmd_gaming,
    "clear-bug": cmd_clear_bug,
    "run": cmd_run,
    "add-autostart": lambda a: cmd_autostart(a, True),
    "remove-autostart": lambda a: cmd_autostart(a, False),
}


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help") or argv[0] not in COMMANDS:
        print(USAGE)
        return 0 if not argv or argv[0] in ("-h", "--help", "help") else 1
    return COMMANDS[argv[0]](argv[1:]) or 0
