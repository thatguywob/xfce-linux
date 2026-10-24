"""Contract tests for reusable BuildStream dashboard components."""

from tools.bst_dashboard.model import State
from tools.bst_dashboard.parser import parse_line


def event(status, *, build_hash="abcdef"):
    return (
        f"[00:00:01][{build_hash}][build:xfce-linux/session.bst] "
        f"{status:<7} xfce/session/{build_hash}-build.log"
    )


def test_parser_updates_injected_state_without_dashboard_runtime():
    state = State()

    parse_line(event("START"), state)
    parse_line(event("SUCCESS"), state)

    assert state.active == {}
    assert state.success_count == 1
    assert state.completed[0]["element"] == "xfce-linux/session.bst"


def test_state_snapshot_uses_injected_runtime_adapters():
    state = State(
        build_running=lambda: True,
        sysinfo=lambda: {"cpu_pct": 42.0},
    )

    snapshot = state.snapshot()

    assert snapshot["build_running"] is True
    assert snapshot["sysinfo"] == {"cpu_pct": 42.0}
