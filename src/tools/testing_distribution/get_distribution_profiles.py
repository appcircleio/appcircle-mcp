"""Get testing distribution profiles tool."""

from typing import Dict, Any, Optional

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...schemas.responses import success_response

TOOL_NAME = "get_distribution_profiles"


def _trim_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of the profile without settings.password."""
    out = dict(profile)
    settings = out.get("settings")
    if isinstance(settings, dict):
        out["settings"] = dict(settings)
        out["settings"].pop("password", None)
    return out


@mcp.tool()
async def get_distribution_profiles(
    page: Optional[int] = None,
    size: Optional[int] = None,
    search: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get testing distribution profiles for the current organization (paginated).

    Returns a list of distribution profiles with their IDs, names, iOS and Android
    app versions, settings details, and testing group information.
    Optionally filter by profile name using the search parameter.

    Args:
        page: Page number (1-based). Default: 1.
        size: Page size (1-100). Default: 25. Values above 100 are capped at 100.
        search: Optional search term to filter profiles by name (case-insensitive partial match).
                For example, search="iOS" will return profiles with "iOS" in their name.

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (list of distribution profile objects), meta (count, page, page_size, search_term).
        - Error: success (false), error (tool, type, message, details).
        Profile objects exclude settings.password.

    Examples:
        Get first page (default size 25): get_distribution_profiles()
        Get page 2 with 10 items: get_distribution_profiles(page=2, size=10)
        Search for iOS profiles: get_distribution_profiles(search="iOS")
    """
    try:
        # Apply defaults and validation
        page = 1 if page is None or page < 1 else page
        size = 25 if size is None else size
        if size > 100:
            logger.warning(f"Requested size {size} exceeds maximum 100, using 100")
            size = 100
        if size < 1:
            size = 1

        params = {
            "page": str(page),
            "size": str(size),
        }
        if search is not None:
            params["search"] = search

        logger.debug(f"Fetching distribution profiles - page: {page}, size: {size}, search: {search}")

        api_client = ApiClient()
        response = await api_client.get("/distribution/v2/profiles", params=params)

        # Support both raw list and wrapper (e.g. {"data": [...], "pagination": ..., ...})
        if isinstance(response, list):
            profiles_raw = response
        elif isinstance(response, dict):
            profiles_raw = response.get("data") or response.get("items") or response.get("profiles") or []
            if not isinstance(profiles_raw, list):
                profiles_raw = []
        else:
            profiles_raw = []

        data = [_trim_profile(p) for p in profiles_raw]
        count = len(data)

        if search:
            logger.info(f"Successfully retrieved {count} distribution profiles matching '{search}' (page {page})")
        else:
            logger.info(f"Successfully retrieved {count} distribution profiles (page {page})")

        meta = {
            "count": count,
            "page": page,
            "page_size": size,
            "search_term": search,
        }

        return success_response(data=data, meta=meta)

    except Exception as e:
        logger.error(f"Failed to get distribution profiles: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
