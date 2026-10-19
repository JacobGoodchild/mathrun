"""Alerts for verified candidates: desktop pop-up and optional ntfy.sh push.

The ntfy message is deliberately minimal: the problem name and "candidate
verified, check dashboard". No numbers, no paths, nothing personal.
"""

import logging
import shutil
import subprocess
import urllib.request

log = logging.getLogger("mathrun")


def message_for(problem_name):
    return "%s: candidate verified, check dashboard" % problem_name


def desktop(title, body):
    if not shutil.which("notify-send"):
        return False
    try:
        subprocess.run(["notify-send", "--urgency=critical", "--app-name=mathrun", title, body],
                       timeout=10, capture_output=True)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def ntfy(cfg, problem_name):
    a = cfg["alerts"]
    topic = (a.get("ntfy_topic") or "").strip()
    if not topic:
        return False
    server = (a.get("ntfy_server") or "https://ntfy.sh").rstrip("/")
    if not server.startswith("https://"):
        log.warning("ntfy_server must be https://; alert not sent")
        return False
    req = urllib.request.Request(server + "/" + urllib.request.quote(topic),
                                 data=message_for(problem_name).encode("utf-8"), method="POST")
    req.add_header("Title", "mathrun")
    req.add_header("Priority", "high")
    email = (a.get("ntfy_email") or "").strip()
    if email:
        req.add_header("Email", email)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return 200 <= r.status < 300
    except Exception as e:  # network trouble must never crash the runner
        log.warning("ntfy alert failed: %s", e)
        return False


def send_verified(cfg, problem_name):
    sent = []
    if cfg["alerts"].get("desktop", True) and desktop(
            "mathrun: VERIFIED CANDIDATE",
            message_for(problem_name) + " (needs human review)"):
        sent.append("desktop")
    if ntfy(cfg, problem_name):
        sent.append("ntfy")
    return sent
