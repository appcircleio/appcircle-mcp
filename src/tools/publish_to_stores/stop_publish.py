"""Stop publish tool (write/action)."""

from typing import Any, Dict, Literal, Optional

from mcp.types import ToolAnnotations

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.validation import path_segment
from ...core.error_handler import handle_write_api_error
from ...core.logger import logger
from ...schemas.responses import success_response

TOOL_NAME = "stop_publish"

PlatformType = Literal["ios", "android"]


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=True,
    )
)
async def stop_publish(
    platform_type: PlatformType,
    profile_id: str,
    publish_id: str,
    step_id: Optional[str] = None,
    organization_pool_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    SIDE EFFECT: Cancels a running publish flow run. This is a write/action tool
    -- it stops real, in-progress publishing work; it cannot be resumed afterward.

    Args:
        platform_type: Platform type ("ios" or "android").
        profile_id: The publish profile ID (e.g. UUID).
        publish_id: The publish flow run ID (the "id" field from get_publish_details).
        step_id: Optional step ID (a step's "id" field from get_publish_details' steps list).
        organization_pool_id: Optional organization pool ID (e.g. UUID).

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data ({"task_id": <uuid>}), meta (step_id, organization_pool_id).
        - Error: success (false), error (tool, type, message, details). type is invalid_state
          (HTTP 409/422) when the publish run has already finished and can no longer be cancelled.

    Examples:
        Stop a publish flow: stop_publish(platform_type="ios", profile_id="p-uuid", publish_id="pub-uuid")
    """
    try:
        params: Dict[str, Any] = {}
        if organization_pool_id is not None:
            params["organizationPoolId"] = organization_pool_id
        if step_id is not None:
            params["stepId"] = step_id

        logger.debug(
            f"Stopping publish - platform_type: {platform_type}, profile_id: {profile_id}, "
            f"publish_id: {publish_id}, params: {params}"
        )

        api_client = ApiClient()
        response = await api_client.post(
            f"/publish/v3/profiles/{platform_type}/{path_segment(profile_id, 'profile_id')}/publish/{path_segment(publish_id, 'publish_id')}/cancel",
            params=params,
        )

        task_id = response if isinstance(response, str) else None
        data = {"task_id": task_id} if task_id is not None else (response if isinstance(response, dict) else {})

        logger.info(f"Successfully stopped publish {publish_id}: task_id={task_id}")

        meta = {
            "step_id": step_id,
            "organization_pool_id": organization_pool_id,
        }
        return success_response(data=data, meta=meta)

    except Exception as e:
        logger.error(f"Failed to stop publish: {str(e)}")
        return handle_write_api_error(e, TOOL_NAME)
