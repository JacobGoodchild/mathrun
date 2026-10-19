"""Opt-in autostart as a systemd *user* service (no sudo, nothing system-wide).

The only file mathrun ever writes outside the repo is
``~/.config/systemd/user/mathrun.service``, and only when you run
``./mathrun add-autostart``. ``./mathrun remove-autostart`` deletes it.
"""

import os
import shutil
import subprocess
import sys

from . import paths

UNIT_NAME = "mathrun.service"


def unit_path():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "systemd", "user", UNIT_NAME)


def unit_text():
    return """[Unit]
Description=mathrun background searchers (lowest priority)
After=default.target

[Service]
Type=simple
WorkingDirectory={repo}
ExecStart={py} -m mathrun_core.runner
Nice=19
IOSchedulingClass=idle
Restart=on-failure
RestartSec=60
KillMode=control-group
TimeoutStopSec=30

[Install]
WantedBy=default.target
""".format(repo=paths.REPO, py=sys.executable)


def _systemctl(*args):
    if not shutil.which("systemctl"):
        return 1, "systemctl not found"
    r = subprocess.run(["systemctl", "--user"] + list(args), capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def add():
    path = unit_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(unit_text())
    print("Wrote %s" % path)
    _systemctl("daemon-reload")
    code, out = _systemctl("enable", UNIT_NAME)
    if code:
        print("Could not enable the service: %s" % out)
        return 1
    print("mathrun will now start by itself whenever you log in.")
    print("(It is not started right now; use ./mathrun start, or log out and in.)")
    return 0


def remove():
    path = unit_path()
    _systemctl("disable", "--now", UNIT_NAME)
    if os.path.exists(path):
        os.unlink(path)
        print("Removed %s" % path)
    else:
        print("No autostart file was installed.")
    _systemctl("daemon-reload")
    return 0
