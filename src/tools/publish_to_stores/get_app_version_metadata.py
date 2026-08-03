"""Get app version metadata tool."""

from typing import Any, Dict, Literal

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...schemas.responses import success_response

TOOL_NAME = "get_app_version_metadata"

PlatformType = Literal["ios", "android"]

# Key to exclude from appReviewInformation (security)
EXCLUDED_KEY = "demoPassword"


def _trim_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of the metadata without appReviewInformation.demoPassword."""
    out = dict(metadata)
    review_info = out.get("appReviewInformation")
    if isinstance(review_info, dict):
        out["appReviewInformation"] = dict(review_info)
        out["appReviewInformation"].pop(EXCLUDED_KEY, None)
    return out


@mcp.tool()
async def get_app_version_metadata(
    platform_type: PlatformType,
    profile_id: str,
    app_version_id: str,
) -> Dict[str, Any]:
    """
    Get store listing metadata for a single app version.

    Returns app review information (reviewer contact, demo user, notes),
    localizations, release information (automatic/phased release settings), and
    app version information (version, copyright) for the given app version.
    appReviewInformation.demoPassword is excluded from the response.

    Args:
        platform_type: Platform type ("ios" or "android").
        profile_id: The publish profile ID (e.g. UUID).
        app_version_id: The app version ID (e.g. UUID).

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (metadata object: appReviewInformation, localizations,
          id, profileId, appVersionId, organizationId, createDate, updateDate, releaseInformation,
          appVersionInformation), meta (empty).
        - Error: success (false), error (tool, type, message, details).

    Examples:
        Get app version metadata: get_app_version_metadata(platform_type="ios", profile_id="uuid", app_version_id="version-uuid")
    """
    try:
        logger.debug(
            f"Fetching app version metadata - platform_type: {platform_type}, "
            f"profile_id: {profile_id}, app_version_id: {app_version_id}"
        )

        api_client = ApiClient()
        response = await api_client.get(
            f"/publish/v2/profiles/{platform_type}/{profile_id}/app-versions/{app_version_id}/metadata"
        )

        if not isinstance(response, dict):
            response = {}

        data = _trim_metadata(response)

        logger.info(
            f"Successfully retrieved app version metadata for {platform_type}/{profile_id}/{app_version_id}"
        )

        return success_response(data=data, meta={})

    except Exception as e:
        logger.error(f"Failed to get app version metadata: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
