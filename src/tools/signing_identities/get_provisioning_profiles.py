"""Get provisioning profiles tool."""

from typing import Any, Dict, List, Optional

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...schemas.responses import success_response

TOOL_NAME = "get_provisioning_profiles"

ENDPOINT = "/signing-identity/v2/provisioning-profiles"

# Keys to exclude from provisioning profile response (sensitive / not needed for tool contract)
EXCLUDED_PROFILE_KEYS = (
    "binary",
    "metaData",
    "certificateThumbPrints",
    "provisionedDevices",
    "connectApiKeyId",
)


def _normalize_provisioning_profiles_response(response: Any) -> List[Dict[str, Any]]:
    """Return list of provisioning profiles from API response (list or wrapper)."""
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        return (
            response.get("data")
            or response.get("items")
            or response.get("provisioningProfiles")
            or []
        )
    return []


def _trim_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of the profile without excluded keys."""
    out = dict(profile)
    for key in EXCLUDED_PROFILE_KEYS:
        out.pop(key, None)
    return out


@mcp.tool()
async def get_provisioning_profiles(app_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Get provisioning profiles for the organization.

    Returns the list of provisioning profiles (e.g. iOS/macOS) registered
    in Appcircle. Sensitive/large fields (binary, metaData, certificateThumbPrints,
    provisionedDevices, connectApiKeyId) are omitted from the response.
    Optionally filter by app (bundle) ID.

    Args:
        app_id: Optional app (bundle) ID to filter provisioning profiles (e.g. com.example.app).

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (list of provisioning profile objects), meta (count, filters).
        - Error: success (false), error (tool, type, message, details).

    Examples:
        Get all provisioning profiles: get_provisioning_profiles()
        Filter by app: get_provisioning_profiles(app_id="com.example.myapp")
    """
    try:
        params: Optional[Dict[str, Any]] = None
        if app_id is not None and str(app_id).strip():
            params = {"appId": str(app_id).strip()}
            logger.debug(f"Fetching provisioning profiles - app_id: {app_id}")
        else:
            logger.debug("Fetching provisioning profiles")

        api_client = ApiClient()
        response = await api_client.get(ENDPOINT, params=params)

        items_raw = _normalize_provisioning_profiles_response(response)
        items = [_trim_profile(p) for p in items_raw]
        count = len(items)

        meta: Dict[str, Any] = {"count": count}
        if params:
            meta["filters"] = {"app_id": params["appId"]}

        logger.info(f"Successfully retrieved {count} provisioning profiles")

        return success_response(data=items, meta=meta)

    except Exception as e:
        logger.error(f"Failed to get provisioning profiles: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
