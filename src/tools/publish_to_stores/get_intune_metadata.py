"""Get Intune metadata tool."""

from typing import Any, Dict, Literal

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.validation import path_segment
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...schemas.responses import success_response

TOOL_NAME = "get_intune_metadata"

PlatformType = Literal["ios", "android"]


@mcp.tool()
async def get_intune_metadata(
    platform_type: PlatformType,
    profile_id: str,
    app_version_id: str,
) -> Dict[str, Any]:
    """
    Get Microsoft Intune app metadata for a single app version.

    Returns the Intune app record synced for this app version: display name,
    description, publisher/owner/developer, bundle ID, version, publishing
    state, applicable device types, categories, and Intune-side timestamps.

    Args:
        platform_type: Platform type ("ios" or "android").
        profile_id: The publish profile ID (e.g. UUID).
        app_version_id: The app version ID (e.g. UUID).

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (Intune metadata object: id, profileId,
          appVersionId, intuneAppId, displayName, description, publisher, publishingState,
          bundleId, version, versionCode, applicableDeviceType, categories, etc.), meta (empty).
        - Error: success (false), error (tool, type, message, details).

    Examples:
        Get Intune metadata: get_intune_metadata(platform_type="ios", profile_id="uuid", app_version_id="version-uuid")
    """
    try:
        logger.debug(
            f"Fetching Intune metadata - platform_type: {platform_type}, "
            f"profile_id: {profile_id}, app_version_id: {app_version_id}"
        )

        api_client = ApiClient()
        response = await api_client.get(
            f"/publish/v2/profiles/{platform_type}/{path_segment(profile_id, 'profile_id')}/app-versions/{path_segment(app_version_id, 'app_version_id')}/intune/metadata"
        )

        if not isinstance(response, dict):
            response = {}

        logger.info(
            f"Successfully retrieved Intune metadata for {platform_type}/{profile_id}/{app_version_id}"
        )

        return success_response(data=response, meta={})

    except Exception as e:
        logger.error(f"Failed to get Intune metadata: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
