"""Get build configuration details tool."""

from typing import Dict, Any

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.validation import path_segment
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...schemas.responses import success_response

TOOL_NAME = "get_build_configuration_details"


@mcp.tool()
async def get_build_configuration_details(
    profile_id: str,
    configuration_id: str,
) -> Dict[str, Any]:
    """
    Get a single build configuration by profile ID and configuration ID.

    Returns the build configuration with the given IDs, including configuration name,
    platform settings, workflows, signing identities, distribution and publish profile
    references, and related metadata (item1: configuration object, item2: optional extra).

    Args:
        profile_id: The build profile ID (e.g. UUID).
        configuration_id: The build configuration ID (e.g. UUID).

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (object with item1: configuration details, item2: optional), meta (empty).
        - Error: success (false), error (tool, type, message, details).

    Examples:
        Get configuration details: get_build_configuration_details(profile_id="uuid", configuration_id="config-uuid")
    """
    try:
        logger.debug(
            f"Fetching build configuration details - profile_id: {profile_id}, configuration_id: {configuration_id}"
        )

        api_client = ApiClient()
        response = await api_client.get(
            f"/build/v2/profiles/{path_segment(profile_id, 'profile_id')}/configurations/{path_segment(configuration_id, 'configuration_id')}"
        )

        if not isinstance(response, dict):
            response = {}

        logger.info(
            f"Successfully retrieved build configuration details for {profile_id}/{configuration_id}"
        )

        return success_response(data=response, meta={})

    except Exception as e:
        logger.error(f"Failed to get build configuration details: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
