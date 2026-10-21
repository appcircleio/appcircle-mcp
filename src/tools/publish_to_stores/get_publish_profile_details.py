"""Get publish profile details tool."""

from typing import Dict, Any, Optional, Literal

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.validation import path_segment
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...schemas.responses import success_response

TOOL_NAME = "get_publish_profile_details"

PlatformType = Literal["ios", "android"]

# Key to exclude from profile and app versions (security)
EXCLUDED_KEY = "signedCertThumbPrint"


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


def _build_meta_from_pagination(
    pagination: Optional[Dict[str, Any]], page: int, size: int, platform_type: str
) -> Dict[str, Any]:
    """Build meta dict from API pagination object (app versions pagination)."""
    base = {"platform_type": platform_type, "page": page, "page_size": size}
    if not isinstance(pagination, dict):
        return base
    base["page"] = pagination.get("page", page)
    base["page_size"] = pagination.get("perPage", size)
    base["page_count"] = pagination.get("pageCount")
    base["total_count"] = pagination.get("totalCount")
    base["enable_previous"] = pagination.get("enablePrevious")
    base["enable_next"] = pagination.get("enableNext")
    return base


@mcp.tool()
async def get_publish_profile_details(
    platform_type: PlatformType,
    profile_id: str,
    page: Optional[int] = None,
    size: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Get a single publish profile by platform type and ID (with optional app versions pagination).

    Returns the publish profile with the given ID for the given platform, including name,
    configuration, and a paginated list of app versions. Use page and size to paginate app versions.
    The returned profile and each app version exclude signedCertThumbPrint.

    Args:
        platform_type: Platform type ("ios" or "android").
        profile_id: The publish profile ID (e.g. UUID).
        page: Page number for app versions (1-based). Default: 1.
        size: Page size for app versions (1-100). Default: 25. Values above 100 are capped at 100.

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (single publish profile object with appVersions), meta (app-versions pagination, platform_type).
        - Error: success (false), error (tool, type, message, details).
        Profile and app versions exclude signedCertThumbPrint.

    Examples:
        Get profile details: get_publish_profile_details(platform_type="ios", profile_id="uuid-here")
        Get first page of app versions (5 per page): get_publish_profile_details(platform_type="ios", profile_id="uuid", page=1, size=5)
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
            "addAppVersions": "true",
        }

        logger.debug(
            f"Fetching publish profile details - platform_type: {platform_type}, profile_id: {profile_id}, page: {page}, size: {size}"
        )

        api_client = ApiClient()
        response = await api_client.get(
            f"/publish/v2/profiles/{platform_type}/{path_segment(profile_id, 'profile_id')}",
            params=params,
        )

        if not isinstance(response, dict):
            response = {}

        profile_raw = response.get("data") or response.get("profile") or response
        if not isinstance(profile_raw, dict):
            profile_raw = {}

        pagination = response.get("pagination")
        meta = _build_meta_from_pagination(pagination, page, size, platform_type)

        data = _trim_profile(profile_raw)

        logger.info(
            f"Successfully retrieved publish profile details for {platform_type}/{profile_id} (page {page})"
        )

        return success_response(data=data, meta=meta)

    except Exception as e:
        logger.error(f"Failed to get publish profile details: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
