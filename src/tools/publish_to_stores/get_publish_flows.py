"""Get publish flows tool."""

from typing import Any, Dict, List, Literal

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.validation import path_segment
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...schemas.responses import success_response

TOOL_NAME = "get_publish_flows"

PlatformType = Literal["ios", "android"]


def _normalize_flows_response(response: Any) -> List[Dict[str, Any]]:
    """Return list of publish flows from API response (list or wrapper)."""
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        data = response.get("data") or response.get("items") or response.get("publishFlows") or []
        return data if isinstance(data, list) else []
    return []


@mcp.tool()
async def get_publish_flows(
    platform_type: PlatformType,
    profile_id: str,
) -> Dict[str, Any]:
    """
    Get the publish flows configured for a publish profile.

    Returns each publish flow's name, ID, and full flow document (YAML text
    defining the flow's ordered steps, each step's component/version/inputs/
    outputs).

    Args:
        platform_type: Platform type ("ios" or "android").
        profile_id: The publish profile ID (e.g. UUID).

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (list of flow objects: organizationId, profileId,
          flowName, flowDocument, id, events), meta (count).
        - Error: success (false), error (tool, type, message, details).

    Examples:
        Get publish flows: get_publish_flows(platform_type="ios", profile_id="uuid")
    """
    try:
        logger.debug(f"Fetching publish flows - platform_type: {platform_type}, profile_id: {profile_id}")

        api_client = ApiClient()
        response = await api_client.get(f"/publish/v2/profiles/{platform_type}/{path_segment(profile_id, 'profile_id')}/publishflows")

        data = _normalize_flows_response(response)
        count = len(data)

        logger.info(f"Successfully retrieved {count} publish flows for {platform_type}/{profile_id}")

        return success_response(data=data, meta={"count": count})

    except Exception as e:
        logger.error(f"Failed to get publish flows: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
