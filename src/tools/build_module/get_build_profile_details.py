"""Get build profile details tool."""

from typing import Dict, Any, Optional

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.validation import path_segment
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...schemas.responses import success_response

TOOL_NAME = "get_build_profile_details"

# Keys to exclude from profile response (security)
EXCLUDED_PROFILE_KEYS = ("connectionEnvironmentKey", "webhookSecret")


def _trim_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of the profile without excluded keys."""
    out = dict(profile)
    for key in EXCLUDED_PROFILE_KEYS:
        out.pop(key, None)
    return out


def _normalize_configurations_response(response: Any) -> list:
    """Return list of configurations from API response (list or wrapper)."""
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        return response.get("data") or response.get("items") or response.get("configurations") or []
    return []


@mcp.tool()
async def get_build_profile_details(
    profile_id: str,
    configurations: Optional[bool] = False,
) -> Dict[str, Any]:
    """
    Get a single build profile by ID, optionally including its build configurations.

    Returns the build profile with the given ID, including name, platform type,
    repository information, build status, and optionally the list of configurations
    (when configurations=True, calls GET /build/v2/profiles/{profileId}/configurations).
    The returned profile excludes connectionEnvironmentKey and webhookSecret.

    Args:
        profile_id: The build profile ID (e.g. UUID).
        configurations: If True, also fetch the profile's build configurations and
            include them in data.configurations. Default: False.

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (build profile object; if configurations=True
          then data also has a "configurations" key with the list), meta (empty).
        - Error: success (false), error (tool, type, message, details).
        Profile object excludes connectionEnvironmentKey and webhookSecret.

    Examples:
        Get details for a profile: get_build_profile_details(profile_id="uuid-here")
        Get profile with configurations: get_build_profile_details(profile_id="uuid", configurations=True)
    """
    try:
        logger.debug(
            f"Fetching build profile details - profile_id: {profile_id}, configurations: {configurations}"
        )

        api_client = ApiClient()
        response = await api_client.get(f"/build/v2/profiles/{path_segment(profile_id, 'profile_id')}")

        # Support raw object or wrapper (e.g. {"data": {...}})
        if isinstance(response, dict):
            profile_raw = response.get("data") or response.get("profile") or response
        else:
            profile_raw = response
        if not isinstance(profile_raw, dict):
            profile_raw = {}

        data = _trim_profile(profile_raw)

        if configurations:
            config_response = await api_client.get(
                f"/build/v2/profiles/{path_segment(profile_id, 'profile_id')}/configurations"
            )
            data["configurations"] = _normalize_configurations_response(config_response)

        logger.info(
            f"Successfully retrieved build profile details for {profile_id}"
            + (" (with configurations)" if configurations else "")
        )

        return success_response(data=data, meta={})

    except Exception as e:
        logger.error(f"Failed to get build profile details: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
