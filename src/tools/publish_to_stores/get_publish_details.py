"""Get publish details tool."""

from typing import Any, Dict, Literal

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...schemas.responses import success_response

TOOL_NAME = "get_publish_details"

PlatformType = Literal["ios", "android"]


@mcp.tool()
async def get_publish_details(
    platform_type: PlatformType,
    profile_id: str,
    app_version_id: str,
) -> Dict[str, Any]:
    """
    Get the publish flow run details for a single app version.

    Returns the publish flow's status, timing, and its ordered steps, each
    with the step's component, status, run history (flowStepHistories, with
    log resource IDs and artifacts), and inputs/outputs.

    Args:
        platform_type: Platform type ("ios" or "android").
        profile_id: The publish profile ID (e.g. UUID).
        app_version_id: The app version ID (e.g. UUID).

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (publish flow object: id, profileId, appversionId,
          name, startedOn, completedOn, status, steps (list, each with flowStepHistories/
          artifacts/logResourceId), triggerType, etc.), meta (empty).
        - Error: success (false), error (tool, type, message, details).

    Examples:
        Get publish details: get_publish_details(platform_type="ios", profile_id="uuid", app_version_id="version-uuid")
    """
    try:
        logger.debug(
            f"Fetching publish details - platform_type: {platform_type}, "
            f"profile_id: {profile_id}, app_version_id: {app_version_id}"
        )

        api_client = ApiClient()
        response = await api_client.get(
            f"/publish/v2/profiles/{platform_type}/{profile_id}/app-versions/{app_version_id}/publish"
        )

        if not isinstance(response, dict):
            response = {}

        logger.info(
            f"Successfully retrieved publish details for {platform_type}/{profile_id}/{app_version_id}"
        )

        return success_response(data=response, meta={})

    except Exception as e:
        logger.error(f"Failed to get publish details: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
