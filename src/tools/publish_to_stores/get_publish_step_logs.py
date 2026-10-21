"""Get publish step logs tool."""

from typing import Any, Dict, Literal, Optional

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.validation import path_segment
from ...core.error_handler import handle_api_error
from ...core.log_utils import (
    DEFAULT_MAX_BYTES,
    DEFAULT_TAIL_LINES,
    FULL_LOG_MAX_BYTES,
    MAX_TAIL_LINES,
    cap_to_max_bytes,
    parse_steps,
)
from ...core.logger import logger
from ...schemas.responses import success_response, error_response

TOOL_NAME = "get_publish_step_logs"

PlatformType = Literal["ios", "android"]


@mcp.tool()
async def get_publish_step_logs(
    platform_type: PlatformType,
    profile_id: str,
    publish_id: str,
    step_id: str,
    step: Optional[str] = None,
    full_log: bool = False,
    tail_lines: Optional[int] = None,
    grep: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get the logs for a publish flow run, optionally scoped to a single step.

    The log returned for a given step_id may include other steps of the same
    publish flow run in the same log text (Appcircle stores one combined log
    per run). By default returns only the tail of the log (last 200 lines,
    capped at 64 KB) to avoid flooding the model's context. Pass full_log=True
    for the entire log instead (still capped at 256 KB as a safety net). Pass
    step to scope the output to one workflow step's log block, matched by its
    exact name as it appears in the log (e.g. "Send to Microsoft Intune") --
    the log marks each step with "Step started: <name>" / "Step completed:
    <name>[, Ver: <version>]" lines. Use grep to keep only lines containing a
    case-insensitive substring before truncation (e.g. grep="error").

    Args:
        platform_type: Platform type ("ios" or "android").
        profile_id: The publish profile ID (e.g. UUID).
        publish_id: The publish flow run ID (the "id" field from get_publish_details).
        step_id: The step ID (a step's "id" field from get_publish_details' steps list).
        step: Optional exact step name (case-insensitive) to scope the output to
            just that step's log block. If no step with this name is found, returns
            a validation_error listing the step names actually present in the log.
        full_log: If True, return the entire log (or entire step, if step is given)
            instead of the default tail. Still capped at 256 KB. Default: False.
        tail_lines: Number of lines to keep from the end when not using full_log.
            Default: 200. Max: 1000. Ignored when full_log=True.
        grep: Case-insensitive substring filter applied to lines before truncation.

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (the resulting log text), meta (total_lines,
          returned_lines, truncated, full_log, step, steps -- the ordered list of all
          step names found in the log -- and grep, when provided).
        - Error: success (false), error (tool, type, message, details). When step is
          given but not found, type is validation_error and details.available_steps
          lists the step names found in the log.

    Examples:
        Default tail: get_publish_step_logs(platform_type="ios", profile_id="p-uuid", publish_id="pub-uuid", step_id="step-uuid")
        Full log: get_publish_step_logs(platform_type="ios", profile_id="p-uuid", publish_id="pub-uuid", step_id="step-uuid", full_log=True)
        One step: get_publish_step_logs(platform_type="ios", profile_id="p-uuid", publish_id="pub-uuid", step_id="step-uuid", step="Send to Microsoft Intune")
        Errors only: get_publish_step_logs(platform_type="ios", profile_id="p-uuid", publish_id="pub-uuid", step_id="step-uuid", grep="error")
    """
    try:
        logger.debug(
            f"Fetching publish step logs - platform_type: {platform_type}, "
            f"profile_id: {profile_id}, publish_id: {publish_id}, step_id: {step_id}"
        )

        api_client = ApiClient()
        raw_text = await api_client.get_text(
            f"/publish/v2/profiles/{platform_type}/{path_segment(profile_id, 'profile_id')}/publish/{path_segment(publish_id, 'publish_id')}/step/{path_segment(step_id, 'step_id')}/logs"
        )

        lines = raw_text.splitlines()
        parsed_steps = parse_steps(lines)
        step_names = [s["name"] for s in parsed_steps]

        scoped_lines = lines
        resolved_step: Optional[str] = None
        if step is not None:
            match = next(
                (s for s in parsed_steps if s["name"].lower() == step.strip().lower()), None
            )
            if match is None:
                return error_response(
                    tool=TOOL_NAME,
                    type="validation_error",
                    message=f"No step named '{step}' found in this publish run's log.",
                    details={"requested_step": step, "available_steps": step_names},
                )
            resolved_step = match["name"]
            scoped_lines = lines[match["start"] : match["end"] + 1]

        if grep:
            needle = grep.lower()
            scoped_lines = [line for line in scoped_lines if needle in line.lower()]

        total_lines = len(scoped_lines)

        if full_log:
            result_lines, byte_truncated = cap_to_max_bytes(scoped_lines, FULL_LOG_MAX_BYTES)
        else:
            tail_n = DEFAULT_TAIL_LINES if tail_lines is None else tail_lines
            if tail_n > MAX_TAIL_LINES:
                logger.warning(
                    f"Requested tail_lines {tail_n} exceeds maximum {MAX_TAIL_LINES}, "
                    f"using {MAX_TAIL_LINES}"
                )
                tail_n = MAX_TAIL_LINES
            if tail_n < 1:
                tail_n = 1
            result_lines, byte_truncated = cap_to_max_bytes(
                scoped_lines[-tail_n:], DEFAULT_MAX_BYTES
            )

        truncated = byte_truncated or len(result_lines) < total_lines

        meta: Dict[str, Any] = {
            "total_lines": total_lines,
            "returned_lines": len(result_lines),
            "truncated": truncated,
            "full_log": full_log,
            "step": resolved_step,
            "steps": step_names,
        }
        if grep:
            meta["grep"] = grep

        logger.info(
            f"Successfully retrieved publish step logs for {platform_type}/{profile_id}/{publish_id}/{step_id} "
            f"({len(result_lines)}/{total_lines} lines, truncated={truncated})"
        )

        return success_response(data="\n".join(result_lines), meta=meta)

    except Exception as e:
        logger.error(f"Failed to get publish step logs: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
