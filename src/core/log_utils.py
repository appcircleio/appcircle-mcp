"""Shared log truncation/step-parsing helpers for tools that fetch plain-text
workflow logs marked with "Step started: <name>" / "Step completed: <name>[,
Ver: <version>]" lines (build logs and publish step logs share this format).
"""

import re
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_TAIL_LINES = 200
MAX_TAIL_LINES = 1000
DEFAULT_MAX_BYTES = 64 * 1024
FULL_LOG_MAX_BYTES = 256 * 1024

# Matched anywhere in the line, not anchored to the "@@[section:...]" prefix
# (the prefix format has at least one observed inconsistency around timestamps).
STEP_STARTED_RE = re.compile(r"Step started:\s*(.+?)\s*$")
STEP_COMPLETED_RE = re.compile(r"Step completed:")


def parse_steps(lines: List[str]) -> List[Dict[str, Any]]:
    """
    Parse "Step started: <name>" / "Step completed: <name>[, Ver: x]" markers into
    ordered step blocks. A step name's "(N)" suffix (e.g. "Custom Script(1)") is
    part of the name as printed in the log; steps are sequential, not nested, per
    the Appcircle agent's log convention. A step missing its "completed" marker
    (e.g. agent crash mid-step) is closed at end of file.
    """
    steps: List[Dict[str, Any]] = []
    current_name: Optional[str] = None
    current_start: Optional[int] = None

    for i, line in enumerate(lines):
        started = STEP_STARTED_RE.search(line)
        if started:
            if current_name is not None:
                steps.append({"name": current_name, "start": current_start, "end": i - 1})
            current_name = started.group(1).strip()
            current_start = i
            continue

        if current_name is not None and STEP_COMPLETED_RE.search(line):
            steps.append({"name": current_name, "start": current_start, "end": i})
            current_name = None
            current_start = None

    if current_name is not None:
        steps.append({"name": current_name, "start": current_start, "end": len(lines) - 1})

    return steps


def cap_to_max_bytes(lines: List[str], max_bytes: int) -> Tuple[List[str], bool]:
    """Keep the tail of lines whose joined UTF-8 size fits max_bytes; always keep >= 1 line."""
    if not lines:
        return lines, False

    sizes = [len(line.encode("utf-8")) for line in lines]
    total = sum(sizes) + max(0, len(lines) - 1)  # + joining newlines
    if total <= max_bytes:
        return lines, False

    cut = len(lines)
    running = 0
    kept_count = 0
    for idx in range(len(lines) - 1, -1, -1):
        addition = sizes[idx] + (1 if kept_count else 0)
        if running + addition > max_bytes and kept_count:
            break
        running += addition
        kept_count += 1
        cut = idx

    kept = lines[cut:]
    if len(kept) == 1 and sizes[cut] > max_bytes:
        encoded = kept[0].encode("utf-8")[-max_bytes:]
        kept = [encoded.decode("utf-8", errors="ignore")]

    return kept, True
