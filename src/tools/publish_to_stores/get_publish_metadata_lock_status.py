"""Get publish metadata lock status tool."""

from typing import Any, Dict, Literal

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...schemas.responses import success_response

TOOL_NAME = "get_publish_metadata_lock_status"

PlatformType = Literal["ios", "android"]


@mcp.tool()
async def get_publish_metadata_lock_status(
    platform_type: PlatformType,
    profile_id: str,
) -> Dict[str, Any]:
    """
    Get whether a publish profile's store metadata is locked for editing.

    A locked profile's metadata (app review info, localizations, release
    info, etc.) cannot be changed until unlocked.

    Args:
        platform_type: Platform type ("ios" or "android").
        profile_id: The publish profile ID (e.g. UUID).

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data ({"locked": <bool>}), meta (empty).
        - Error: success (false), error (tool, type, message, details).

    Examples:
        Get lock status: get_publish_metadata_lock_status(platform_type="ios", profile_id="uuid")
    """
    try:
        logger.debug(
            f"Fetching publish metadata lock status - platform_type: {platform_type}, profile_id: {profile_id}"
        )

        api_client = ApiClient()
        response = await api_client.get(f"/publish/v2/profiles/{platform_type}/{profile_id}/metadata/lock")

        data = response if isinstance(response, dict) else {}

        logger.info(
            f"Successfully retrieved publish metadata lock status for {platform_type}/{profile_id}"
        )

        return success_response(data=data, meta={})

    except Exception as e:
        logger.error(f"Failed to get publish metadata lock status: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
