"""Settings: built-in defaults, overridden by config.local.toml."""

import copy
import os

from . import paths, tomlmini

DEFAULTS = {
    "machine": {
        "workers": 0,
        "nice": 19,
        "max_temp_c": 85.0,
        "resume_temp_c": 75.0,
        "fallback_run_minutes": 20.0,
        "fallback_rest_minutes": 10.0,
        "only_when_idle": False,
        "idle_seconds": 300,
        "pause_for_programs": [],
        "disk_cap_gb": 5.0,
    },
    "problems": {"only": [], "skip": [], "weights": {}},
    "dashboard": {"port": 8471},
    "publish": {
        "enabled": False,
        "remote": "origin",
        "branch": "main",
        "interval_minutes": 60,
    },
    "alerts": {
        "desktop": True,
        "ntfy_topic": "",
        "ntfy_server": "https://ntfy.sh",
        "ntfy_email": "",
    },
}


def local_path():
    return os.environ.get("MATHRUN_CONFIG") or os.path.join(paths.REPO, "config.local.toml")


def _merge(base, over):
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _merge(base[k], v)
        else:
            base[k] = v
    return base


def load(path=None):
    cfg = copy.deepcopy(DEFAULTS)
    path = path or local_path()
    if os.path.exists(path):
        _merge(cfg, tomlmini.load_file(path))
    m = cfg["machine"]
    # Clamp the safety-critical numbers to sane ranges whatever the file says.
    m["nice"] = max(0, min(19, int(m["nice"])))
    m["max_temp_c"] = max(40.0, min(100.0, float(m["max_temp_c"])))
    m["resume_temp_c"] = min(float(m["resume_temp_c"]), m["max_temp_c"] - 2.0)
    m["disk_cap_gb"] = max(0.1, float(m["disk_cap_gb"]))
    # Publishing more than hourly is not allowed.
    cfg["publish"]["interval_minutes"] = max(60, int(cfg["publish"]["interval_minutes"]))
    return cfg


def worker_count(cfg):
    n = int(cfg["machine"]["workers"])
    cores = os.cpu_count() or 1
    if n <= 0:
        n = cores - 1
    return max(1, min(n, cores))
