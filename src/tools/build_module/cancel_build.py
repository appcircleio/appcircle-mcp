"""Cancel build tool (write/action)."""

from typing import Any, Dict

from mcp.types import ToolAnnotations

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.error_handler import handle_write_api_error
from ...core.logger import logger
from ...schemas.responses import success_response

TOOL_NAME = "cancel_build"


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=True,
    )
)
async def cancel_build(task_id: str) -> Dict[str, Any]:
    """
    SIDE EFFECT: Cancels a queued or running build. This is a write/action tool
    -- it stops real, in-progress work; the build cannot be resumed afterward.

    Args:
        task_id: The build's task ID (the "taskId" field returned by trigger_build).

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data ({"task_id": <uuid>, "cancelled": true}), meta (empty).
        - Error: success (false), error (tool, type, message, details). type is invalid_state
          (HTTP 409/422) when the build has already finished and can no longer be cancelled.

    Examples:
        Cancel a build: cancel_build(task_id="task-uuid")
    """
    try:
        logger.debug(f"Cancelling build - task_id: {task_id}")

        api_client = ApiClient()
        await api_client.post(f"/build/v3/queue/{task_id}/cancel")

        logger.info(f"Successfully cancelled build task {task_id}")

        return success_response(data={"task_id": task_id, "cancelled": True}, meta={})

    except Exception as e:
        logger.error(f"Failed to cancel build: {str(e)}")
        return handle_write_api_error(e, TOOL_NAME)
