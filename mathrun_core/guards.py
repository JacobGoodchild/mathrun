"""Computer guards: heat, "someone is using the computer", gaming mode, disk.

``Guards.evaluate()`` returns a small decision dict that the runner obeys:
how many searchers may run right now, and if none, why not. Every probe
fails safe: if something can't be read we choose the cautious option.
"""

import glob
import os
import shutil
import subprocess
import time

from . import paths

CPU_SENSOR_NAMES = ("coretemp", "k10temp", "zenpower", "cpu_thermal", "cpu-thermal",
                    "soc_thermal", "x86_pkg_temp")
ZONE_TYPES = ("x86_pkg_temp", "cpu-thermal", "cpu_thermal", "soc_thermal", "tcpu",
              "acpitz", "k10temp", "coretemp")


def _read_int(path):
    try:
        with open(path) as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


def _plausible(c):
    return c is not None and 5.0 < c < 125.0


def cpu_temp_c(sys_root="/sys"):
    """Hottest CPU temperature in degrees C, or None if it can't be read."""
    best = None
    for hw in glob.glob(os.path.join(sys_root, "class/hwmon/hwmon*")):
        try:
            with open(os.path.join(hw, "name")) as f:
                name = f.read().strip().lower()
        except OSError:
            continue
        if name not in CPU_SENSOR_NAMES:
            continue
        for t in glob.glob(os.path.join(hw, "temp*_input")):
            v = _read_int(t)
            c = v / 1000.0 if v is not None else None
            if _plausible(c):
                best = c if best is None else max(best, c)
    if best is not None:
        return best
    for zone in glob.glob(os.path.join(sys_root, "class/thermal/thermal_zone*")):
        try:
            with open(os.path.join(zone, "type")) as f:
                ztype = f.read().strip().lower()
        except OSError:
            continue
        if ztype not in ZONE_TYPES:
            continue
        v = _read_int(os.path.join(zone, "temp"))
        c = v / 1000.0 if v is not None else None
        if _plausible(c):
            best = c if best is None else max(best, c)
    if best is not None or sys_root != "/sys":
        return best
    return _sensors_cmd_temp()


def _sensors_cmd_temp():
    if not shutil.which("sensors"):
        return None
    try:
        out = subprocess.run(["sensors", "-u"], capture_output=True, text=True,
                             timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    best = None
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("temp") and "_input:" in line:
            try:
                c = float(line.split(":", 1)[1])
            except ValueError:
                continue
            if _plausible(c):
                best = c if best is None else max(best, c)
    return best


def _run(cmd, timeout=3):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


def user_idle_seconds():
    """Seconds since the last keyboard/mouse input, or None if unknown."""
    if os.environ.get("DISPLAY") and shutil.which("xprintidle"):
        out = _run(["xprintidle"])
        if out and out.strip().isdigit():
            return int(out.strip()) / 1000.0
    if shutil.which("gdbus"):
        # GNOME / Cinnamon-on-Mutter style idle monitor.
        out = _run(["gdbus", "call", "--session", "--dest", "org.gnome.Mutter.IdleMonitor",
                    "--object-path", "/org/gnome/Mutter/IdleMonitor/Core",
                    "--method", "org.gnome.Mutter.IdleMonitor.GetIdletime"])
        if out:
            digits = "".join(ch for ch in out if ch.isdigit())
            if digits:
                return int(digits) / 1000.0
    if shutil.which("loginctl"):
        sid = os.environ.get("XDG_SESSION_ID")
        if not sid:
            # started by the systemd user service: find the user's graphical session
            out = _run(["loginctl", "show-user", str(os.getuid()), "-p", "Display", "--value"])
            sid = (out or "").strip() or None
        if sid:
            out = _run(["loginctl", "show-session", sid, "-p", "IdleHint",
                        "-p", "IdleSinceHintMonotonic"])
            if out:
                props = dict(l.split("=", 1) for l in out.splitlines() if "=" in l)
                if props.get("IdleHint") == "no":
                    return 0.0
                if props.get("IdleHint") == "yes":
                    try:
                        since = int(props.get("IdleSinceHintMonotonic", "0")) / 1e6
                        return max(0.0, time.monotonic() - since) if since else 1e9
                    except ValueError:
                        return 1e9
    return None


def running_program_names(proc_root="/proc"):
    names = set()
    for comm in glob.glob(os.path.join(proc_root, "[0-9]*", "comm")):
        try:
            with open(comm) as f:
                names.add(f.read().strip())
        except OSError:
            continue
    return names


def dir_size_bytes(path):
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.lstat(os.path.join(root, name)).st_size
            except OSError:
                pass
    return total


class Guards:
    """Decides, every few seconds, whether searchers may run."""

    def __init__(self, cfg, max_workers, temp_reader=cpu_temp_c, idle_reader=user_idle_seconds,
                 programs_reader=running_program_names, clock=time.monotonic):
        self.m = cfg["machine"]
        self.max_workers = max_workers
        self.temp_reader = temp_reader
        self.idle_reader = idle_reader
        self.programs_reader = programs_reader
        self.clock = clock
        self.too_hot = False
        self.duty_started = clock()
        self.last_disk_check = -1e9
        self.disk_bytes = 0
        self.last = None

    def evaluate(self):
        now = self.clock()
        d = {"workers": self.max_workers, "running": True, "reason": "running",
             "temp_c": None, "idle_s": None, "disk_bytes": self.disk_bytes}

        def pause(reason):
            d.update(workers=0, running=False, reason=reason)
            self.last = d
            return d

        if os.path.exists(paths.control_file("gaming")):
            return pause("gaming mode is on (./mathrun gaming off to resume)")

        wanted = set(self.m.get("pause_for_programs") or [])
        if wanted:
            hit = sorted(wanted & self.programs_reader())
            if hit:
                return pause("paused while %s is running" % ", ".join(hit))

        if now - self.last_disk_check > 60:
            self.last_disk_check = now
            self.disk_bytes = dir_size_bytes(paths.data_dir())
        d["disk_bytes"] = self.disk_bytes
        if self.disk_bytes > float(self.m["disk_cap_gb"]) * 1e9:
            return pause("data folder is over the %.1f GB disk cap" % self.m["disk_cap_gb"])

        temp = self.temp_reader()
        d["temp_c"] = temp
        if temp is None:
            # Can't read the temperature: fall back to a gentle on/off cycle.
            run_s = float(self.m["fallback_run_minutes"]) * 60
            rest_s = float(self.m["fallback_rest_minutes"]) * 60
            phase = (now - self.duty_started) % (run_s + rest_s)
            if phase >= run_s:
                return pause("resting (temperature unreadable, safe on/off cycle)")
        else:
            if self.too_hot and temp <= float(self.m["resume_temp_c"]):
                self.too_hot = False
            elif temp >= float(self.m["max_temp_c"]):
                self.too_hot = True
            if self.too_hot:
                return pause("CPU too hot (%.0f C), cooling down" % temp)

        if self.m.get("only_when_idle"):
            idle = self.idle_reader()
            d["idle_s"] = idle
            if idle is None:
                return pause("only-when-idle mode, but idle time can't be read")
            if idle < float(self.m["idle_seconds"]):
                return pause("computer in use (only-when-idle mode)")

        self.last = d
        return d
