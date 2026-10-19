"""Where things live. Everything stays inside the repo folder."""

import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBLEMS = os.path.join(REPO, "problems")
DOCS = os.path.join(REPO, "docs")


def data_dir():
    # MATHRUN_DATA lets the test-suite use a throwaway folder.
    return os.environ.get("MATHRUN_DATA") or os.path.join(REPO, "data")


def sub(*parts):
    path = os.path.join(data_dir(), *parts)
    return path


def ensure(*parts):
    path = sub(*parts)
    os.makedirs(path, exist_ok=True)
    return path


def state_path(slug):
    return sub("state", slug + ".json")


def history_path(slug):
    return sub("state", slug + ".history.json")


def candidates_dir(slug):
    return sub("candidates", slug)


def status_dir():
    return sub("status")


def logs_dir():
    return sub("logs")


def work_dir(slug):
    return sub("work", slug)


def pid_file():
    return sub("runner.pid")


def lock_file():
    return sub("runner.lock")


def control_file(name):
    """Flag files the CLI drops to talk to the runner (e.g. gaming mode)."""
    return sub("control", name)
