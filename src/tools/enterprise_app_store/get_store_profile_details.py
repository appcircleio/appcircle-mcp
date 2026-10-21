"""Get enterprise app store profile details tool."""

from typing import Dict, Any, Optional

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.validation import path_segment
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...schemas.responses import success_response

TOOL_NAME = "get_store_profile_details"

# Key to exclude from profile and app versions (security)
EXCLUDED_KEY = "signedCertThumbPrint"

# Meaning of each app version's publishType field (int, per the API's own enum
# naming, confirmed against the /app-versions/publish-types/{publishtype} Swagger
# endpoint's path parameter values -- that endpoint itself could not be reached
# via a real call, so this mapping is documentation only, not used for filtering).
APP_VERSION_PUBLISH_TYPES: Dict[int, str] = {0: "None", 1: "Beta", 2: "Live"}


def _trim_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of the profile without signedCertThumbPrint; also trim from each app version."""
    out = dict(profile)
    out.pop(EXCLUDED_KEY, None)
    app_versions = out.get("appVersions")
    if isinstance(app_versions, list):
        out["appVersions"] = []
        for av in app_versions:
            if isinstance(av, dict):
                av_copy = dict(av)
                av_copy.pop(EXCLUDED_KEY, None)
                out["appVersions"].append(av_copy)
            else:
                out["appVersions"].append(av)
    return out


def _build_meta_from_pagination(pagination: Optional[Dict[str, Any]], page: int, size: int) -> Dict[str, Any]:
    """Build meta dict from API pagination object (app versions pagination)."""
    if not isinstance(pagination, dict):
        return {"page": page, "page_size": size}
    return {
        "page": pagination.get("page", page),
        "page_size": pagination.get("perPage", size),
        "page_count": pagination.get("pageCount"),
        "total_count": pagination.get("totalCount"),
        "enable_previous": pagination.get("enablePrevious"),
        "enable_next": pagination.get("enableNext"),
    }


@mcp.tool()
async def get_store_profile_details(
    profile_id: str,
    page: Optional[int] = None,
    size: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Get a single enterprise app store profile by ID (with optional app versions pagination).

    Returns the enterprise app store profile with the given ID, including name,
    configuration, and a paginated list of app versions. Use page and size to paginate app versions.
    The returned profile and each app version exclude signedCertThumbPrint. Each app
    version's publishType field is an int: see APP_VERSION_PUBLISH_TYPES for the
    mapping (0=None, 1=Beta, 2=Live).

    Args:
        profile_id: The enterprise app store profile ID (e.g. UUID).
        page: Page number for app versions (1-based). Default: 1.
        size: Page size for app versions (1-100). Default: 25. Values above 100 are capped at 100.

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (single store profile object with appVersions), meta (app-versions pagination).
        - Error: success (false), error (tool, type, message, details).
        Profile and app versions exclude signedCertThumbPrint. Meta contains page, page_size, total_count, etc.

    Examples:
        Get profile details: get_store_profile_details(profile_id="uuid-here")
        Get first page of app versions (5 per page): get_store_profile_details(profile_id="uuid", page=1, size=5)
    """
    try:
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

        logger.debug(f"Fetching enterprise app store profile details - profile_id: {profile_id}, page: {page}, size: {size}")

        api_client = ApiClient()
        response = await api_client.get(f"/store/v2/profiles/{path_segment(profile_id, 'profile_id')}", params=params)

        if not isinstance(response, dict):
            response = {}

        profile_raw = response.get("data") or response.get("profile") or response
        if not isinstance(profile_raw, dict):
            profile_raw = {}

        pagination = response.get("pagination")
        meta = _build_meta_from_pagination(pagination, page, size)

        data = _trim_profile(profile_raw)

        logger.info(f"Successfully retrieved enterprise app store profile details for {profile_id} (page {page})")

        return success_response(data=data, meta=meta)

    except Exception as e:
        logger.error(f"Failed to get enterprise app store profile details: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
