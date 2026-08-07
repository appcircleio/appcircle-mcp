"""Get testing distribution profiles tool."""

from typing import Dict, Any, List, Optional

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...core.validation import validate_enum_list
from ...schemas.responses import error_response, success_response

TOOL_NAME = "get_distribution_profiles"

# Filter/sort enums, sourced from GET /distribution/v2/profiles/filters
PLATFORMS: Dict[int, str] = {1: "iOS", 2: "Android"}
AUTHENTICATION_TYPES: Dict[int, str] = {1: "None", 3: "Static Login", 4: "LDAP", 5: "SSO"}
SORT_FIELDS: Dict[int, str] = {1: "Profile Name", 2: "Create Date", 3: "Last Upload Date"}
SORT_DIRECTIONS: Dict[int, str] = {1: "ASC", 2: "DESC"}


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
    platform: Optional[List[int]] = None,
    authentication_type: Optional[List[int]] = None,
    sort: Optional[int] = None,
    sort_direction: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Get testing distribution profiles for the current organization (paginated).

    Returns a list of distribution profiles with their IDs, names, iOS and Android
    app versions, settings details, and testing group information.
    Optionally filter by profile name using the search parameter, and/or by
    platform and authentication type. Optionally sort.

    Args:
        page: Page number (1-based). Default: 1.
        size: Page size (1-100). Default: 25. Values above 100 are capped at 100.
        search: Optional search term to filter profiles (case-insensitive partial match on
                profile name; the API's search may also match other profile fields).
                For example, search="iOS" will return profiles with "iOS" in their name,
                and possibly others matching on a different field.
        platform: Optional list of platform codes to filter by. Allowed values:
            1=iOS, 2=Android.
        authentication_type: Optional list of authentication type codes to filter by. Allowed values:
            1=None, 3=Static Login, 4=LDAP, 5=SSO.
        sort: Optional sort field code. Allowed values: 1=Profile Name, 2=Create Date,
            3=Last Upload Date.
        sort_direction: Optional sort direction code. Allowed values: 1=ASC, 2=DESC.

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (list of distribution profile objects), meta (count, page,
          page_size, search_term, platform, authentication_type, sort, sort_direction).
        - Error: success (false), error (tool, type, message, details).
        Profile objects exclude settings.password.

    Examples:
        Get first page (default size 25): get_distribution_profiles()
        Get page 2 with 10 items: get_distribution_profiles(page=2, size=10)
        Search for iOS profiles: get_distribution_profiles(search="iOS")
        Filter by platform and authentication type: get_distribution_profiles(platform=[1], authentication_type=[1])
        Sort by create date descending: get_distribution_profiles(sort=2, sort_direction=2)
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

        for message in (
            validate_enum_list(platform, PLATFORMS, "platform"),
            validate_enum_list(authentication_type, AUTHENTICATION_TYPES, "authentication_type"),
        ):
            if message is not None:
                return error_response(tool=TOOL_NAME, type="validation_error", message=message)
        if sort is not None and sort not in SORT_FIELDS:
            return error_response(
                tool=TOOL_NAME,
                type="validation_error",
                message=f"Invalid sort: {sort}. Allowed values: {sorted(SORT_FIELDS)}",
            )
        if sort_direction is not None and sort_direction not in SORT_DIRECTIONS:
            return error_response(
                tool=TOOL_NAME,
                type="validation_error",
                message=f"Invalid sort_direction: {sort_direction}. Allowed values: {sorted(SORT_DIRECTIONS)}",
            )

        params: Dict[str, Any] = {
            "page": str(page),
            "size": str(size),
        }
        if search is not None:
            params["search"] = search
        if platform is not None:
            params["platform"] = platform
        if authentication_type is not None:
            params["authenticationType"] = authentication_type
        if sort is not None:
            params["sort"] = sort
        if sort_direction is not None:
            params["sortDirection"] = sort_direction

        logger.debug(
            f"Fetching distribution profiles - page: {page}, size: {size}, search: {search}, "
            f"platform: {platform}, authentication_type: {authentication_type}, "
            f"sort: {sort}, sort_direction: {sort_direction}"
        )

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
            "platform": platform,
            "authentication_type": authentication_type,
            "sort": sort,
            "sort_direction": sort_direction,
        }

        return success_response(data=data, meta=meta)

    except Exception as e:
        logger.error(f"Failed to get distribution profiles: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
