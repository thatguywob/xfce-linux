"""BuildStream log parsing independent of dashboard runtime services."""

from __future__ import annotations

import datetime
import os
import re
import time


# Strip ANSI escape codes
ANSI = re.compile(r"\x1b\[[0-9;]*[mGKHF]|\x1b\[[0-9;]*m")

# "=== Build started at Tue Apr 22 03:00:00 IST 2026 ==="
BUILD_HEADER_RE = re.compile(r"=== Build started at (.+?) ===")

# Match a structured BST log line
LINE_RE = re.compile(
    r"^\[(?P<time>[0-9\-:]+)\]\[(?P<hash>[0-9a-f ]+)\]\[(?P<ctx>[^\]]+)\]\s+"
    r"(?P<status>START\s+|SUCCESS|FAILURE|SKIPPED|STATUS\s+|INFO\s+|WARN\s+|PULL\s+)\s*"
    r"(?P<msg>.*)$"
)

# Identify a top-level build event (the line that has the log file path)
BUILD_LOG_RE = re.compile(r"[a-z0-9_\-]+(?:/[a-zA-Z0-9_.\-]+)+\.log$")

# Pipeline Summary lines
PIPELINE_SUMMARY_RE = re.compile(r"^Pipeline Summary\s*$")
SUMMARY_TOTAL_RE    = re.compile(r"^\s+Total:\s+(\d+)")
SUMMARY_QUEUE_RE    = re.compile(r"^\s+(Pull|Build) Queue:\s+processed (\d+), skipped (\d+), failed (\d+)")

# Failure Summary element lines: "    kde-build-meta.bst:kde/plasma/foo.bst:"
FAILURE_ELEM_RE = re.compile(r"^\s+([\w\-]+\.bst:)?kde/[\w/.\-]+\.bst:\s*$")

# Log path line inside failure output: "    /root/.cache/buildstream/logs/gnome/..."
BST_LOG_PATH_RE = re.compile(r"^\s+/root/\.cache/buildstream/logs/(\S+\.log)\s*$")

# Parse element name from context
ELEMENT_RE = re.compile(r"\s*(\w+):(.+)")

# cmake/ninja/meson build progress markers in element logs: "[  42/1234]"
CMAKE_PROGRESS_RE = re.compile(r'\[\s*(\d+)/\s*(\d+)\]')
# Rust/cargo: "   Compiling foo v1.2.3" lines
RUST_COMPILE_RE   = re.compile(r'^\s+Compiling\s+\S+\s+v\S')
# Rust/cargo: "    Finished [optimized] target(s)"
RUST_FINISHED_RE  = re.compile(r'^\s+Finished\s')
# ── Log parser ─────────────────────────────────────────────────────────────────

def reset_state(state):
    """Reset state for a new build (log was truncated/rotated)."""
    def _reset(s):
        s.active.clear()
        s.completed.clear()
        s.failures.clear()
        s._summary_elements.clear()
        s.pulled = 0
        s.success_count = 0
        s.failure_count = 0
        s.cached_count = 0
        # Keep total_elements across resets — stable between runs
        s.recent_lines.clear()
        s.build_start_ts = 0.0
        s.build_end_ts = 0.0
        s.catching_up = True
    state.update(_reset)


def parse_line(raw: str, state):
    clean = ANSI.sub("", raw).rstrip()
    if not clean:
        return

    # Detect new build header ("=== Build started at ... ===")
    hm = BUILD_HEADER_RE.search(clean)
    if hm:
        try:
            # e.g. "Tue Apr 22 03:21:55 IST 2026" — strip timezone abbrev for parsing
            date_str = re.sub(r'\s+[A-Z]{2,5}\s+', ' ', hm.group(1))
            ts = datetime.datetime.strptime(date_str.strip(), "%a %b %d %H:%M:%S %Y").timestamp()
        except Exception:
            ts = time.time()
        def _set_start(s):
            s.active.clear()
            s.completed.clear()
            s.failures.clear()
            s._summary_elements.clear()
            s.pulled = 0
            s.success_count = 0
            s.failure_count = 0
            s.cached_count = 0
            s.recent_lines.clear()
            s.build_end_ts = 0.0
            s.catching_up = True
            s.build_start_ts = ts
            s.recent_lines.append(clean)
        state.update(_set_start)
        return

    # Pipeline Summary lines (unstructured, no BST prefix)
    # "Pipeline Summary" → build has ended; freeze state.
    # The BST "Failure Summary" block appears BEFORE "Pipeline Summary" in the log,
    # so by this point _summary_elements is fully populated. Filter out cascade
    # failures (elements that failed only because a dependency failed, not listed
    # in the Failure Summary).
    if PIPELINE_SUMMARY_RE.match(clean):
        def _pipeline_done(s):
            s.active.clear()
            s.catching_up = False
            if not s.build_end_ts:
                s.build_end_ts = time.time()
            if s._summary_elements:
                # Keep only root-cause failures (those in the Failure Summary).
                # Also reset counters — each Pipeline Summary is authoritative for
                # its sub-run; failures from prior sub-runs are superseded.
                s.failures = [f for f in s.failures if f["element"] in s._summary_elements]
                s.failure_count = len(s.failures)
            # Clear for next sub-run (BST emits multiple Pipeline Summary blocks
            # in one session without a new "Build started" header)
            s._summary_elements.clear()
            s.recent_lines.append(clean)
        state.update(_pipeline_done)
        return

    tm = SUMMARY_TOTAL_RE.match(clean)
    if tm:
        total = int(tm.group(1))
        def _set_total(s):
            s.total_elements = total
        state.update(_set_total)

    qm = SUMMARY_QUEUE_RE.match(clean)
    if qm and qm.group(1) == "Build":
        failed = int(qm.group(4))
        # cached_count and pulled are already tracked live from SKIPPED/SUCCESS Pull events.
        # Only back-fill failure_count from summary if we missed live FAILURE events.
        def _backfill_failures(s, _fl=failed):
            if s.failure_count == 0 and _fl > 0:
                s.failure_count = _fl
        state.update(_backfill_failures)

    # Failure Summary element lines: "    kde-build-meta.bst:kde/plasma/foo.bst:"
    # These are root-cause failures only (BST omits cascade failures from this section).
    fm = FAILURE_ELEM_RE.match(clean)
    if fm:
        raw_elem = clean.strip().rstrip(":")
        short_elem = raw_elem.split(":")[-1]
        def _add_failure_elem(s, _e=short_elem):
            s._summary_elements.add(_e)
            if not any(f["element"] == _e for f in s.failures):
                s.failures.append({"element": _e, "hash": "", "duration": 0, "status": "failure", "log": ""})
                s.failure_count = max(s.failure_count, len(s.failures))
        state.update(_add_failure_elem)

    # Log path line inside failure detail: attach to most recent failure without a log
    lm = BST_LOG_PATH_RE.match(clean)
    if lm:
        bst_logs = os.path.expanduser("~/.cache/buildstream/logs")
        host_log = os.path.join(bst_logs, lm.group(1))
        def _set_fail_log(s, _p=host_log):
            for f in reversed(s.failures):
                if not f.get("log"):
                    f["log"] = _p
                    break
        state.update(_set_fail_log)

    m = LINE_RE.match(clean)
    if not m:
        # Skip deeply-indented lines — these are embedded log/compile output from
        # the Failure Summary block and shouldn't appear in the Recent Log panel.
        if not clean.startswith("        "):
            trunc = clean[:200]
            def _add(s, _l=trunc):
                s.recent_lines.append(_l)
            state.update(_add)
        return

    status   = m.group("status").strip()
    ctx      = m.group("ctx").strip()
    bst_hash = m.group("hash").strip()
    msg      = m.group("msg").strip()

    cm      = ELEMENT_RE.match(ctx)
    action  = cm.group(1) if cm else ctx
    element = cm.group(2).split(":")[-1] if cm else ctx

    short = element
    for prefix in ("kde-build-meta.bst:", "freedesktop-sdk.bst:", "gnome-build-meta.bst:"):
        short = short.replace(prefix, "")

    is_top = bool(BUILD_LOG_RE.search(msg))

    def _add_recent(s):
        s.recent_lines.append(f"[{status:7s}] {short}  {msg}")
    state.update(_add_recent)

    if action == "build" and is_top and status == "START":
        # BST emits relative log paths like "gnome/pkg/hash-build.log"
        # Full path on host: ~/.cache/buildstream/logs/<relative>
        bst_logs = os.path.expanduser("~/.cache/buildstream/logs")
        host_log = os.path.join(bst_logs, msg) if msg.endswith(".log") else ""
        def _start(s, _log=host_log):
            s.active[bst_hash] = {
                "element": short,
                "hash": bst_hash,
                "start": time.time(),
                "log": _log,
            }
        state.update(_start)

    elif action == "build" and is_top and status == "SUCCESS":
        def _done(s):
            entry = s.active.pop(bst_hash, None)
            dur = int(time.time() - entry["start"]) if entry else 0
            s.completed.append({"element": short, "hash": bst_hash, "duration": dur, "status": "success"})
            s.success_count += 1
            s.build_end_ts = time.time()
        state.update(_done)

    elif action == "build" and status == "FAILURE":
        # BST top-level failure says "Command failed" (no log path), so don't
        # require is_top — just check if this hash was actually being tracked.
        def _fail(s):
            entry = s.active.pop(bst_hash, None)
            if entry is None:
                return  # sub-event failure we don't care about
            dur = int(time.time() - entry["start"])
            item = {"element": short, "hash": bst_hash, "duration": dur,
                    "status": "failure", "log": entry.get("log", "")}
            s.completed.append(item)
            # Avoid duplicates from Failure Summary catch-up
            if not any(f["hash"] == bst_hash for f in s.failures):
                # Update existing catch-up entry if present (same element, no hash)
                for f in s.failures:
                    if f["element"] == short and not f["hash"]:
                        f.update(item)
                        break
                else:
                    s.failures.append(item)
            s.failure_count = len(s.failures)
            s.build_end_ts = time.time()
        state.update(_fail)

    elif action == "pull":
        if status == "SKIPPED" and "Pull" in msg:
            def _skip_pull(s):
                s.cached_count += 1
            state.update(_skip_pull)
        elif status == "SUCCESS" and "Pull" in msg:
            def _pull(s):
                s.pulled += 1
            state.update(_pull)
