"""Get metadata locales tool."""

from typing import Any, Dict, List, Literal

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...schemas.responses import success_response

TOOL_NAME = "get_metadata_locales"

PlatformType = Literal["ios", "android"]


def _normalize_locales_response(response: Any) -> List[Dict[str, Any]]:
    """Return list of locales from API response (list or wrapper)."""
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        data = response.get("data") or response.get("items") or response.get("locales") or []
        return data if isinstance(data, list) else []
    return []


@mcp.tool()
async def get_metadata_locales(
    platform_type: PlatformType,
    profile_id: str,
    app_version_id: str,
) -> Dict[str, Any]:
    """
    Get the available store metadata locales for a single app version.

    Returns each locale's display name, code, whether it has been localized
    (has store listing content filled in), and whether it's the app's primary
    locale.

    Args:
        platform_type: Platform type ("ios" or "android").
        profile_id: The publish profile ID (e.g. UUID).
        app_version_id: The app version ID (e.g. UUID).

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (list of locale objects: name, code, localized,
          isPrimary), meta (count).
        - Error: success (false), error (tool, type, message, details).

    Examples:
        Get metadata locales: get_metadata_locales(platform_type="ios", profile_id="uuid", app_version_id="version-uuid")
    """
    try:
        logger.debug(
            f"Fetching metadata locales - platform_type: {platform_type}, "
            f"profile_id: {profile_id}, app_version_id: {app_version_id}"
        )

        api_client = ApiClient()
        response = await api_client.get(
            f"/publish/v2/profiles/{platform_type}/{profile_id}/app-versions/{app_version_id}/metadata/locales"
        )

        data = _normalize_locales_response(response)
        count = len(data)

        logger.info(
            f"Successfully retrieved {count} metadata locales for {platform_type}/{profile_id}/{app_version_id}"
        )

        return success_response(data=data, meta={"count": count})

    except Exception as e:
        logger.error(f"Failed to get metadata locales: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
