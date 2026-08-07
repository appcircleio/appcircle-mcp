"""Get build profiles tool."""

from typing import Dict, Any, List, Optional

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...core.validation import validate_enum_list
from ...schemas.responses import error_response, success_response

TOOL_NAME = "get_build_profiles"

# Keys to exclude from profile response (security)
EXCLUDED_PROFILE_KEYS = ("connectionEnvironmentKey", "webhookSecret")

# Filter/sort enums, sourced from GET /build/v2/profiles/filters
PLATFORMS: Dict[int, str] = {1: "iOS", 2: "Android"}
LAST_BUILD_STATUSES: Dict[int, str] = {
    0: "Success",
    1: "Failed",
    2: "Canceled",
    3: "Timeout",
    90: "Waiting",
    91: "Running",
}
REPOSITORY_SOURCES: Dict[int, str] = {
    1: "GitHub",
    2: "Bitbucket",
    3: "GitLab",
    4: "Azure DevOps",
    6: "Public Repository",
    7: "Private Repository",
    8: "SSH",
}
SORT_FIELDS: Dict[int, str] = {1: "Profile Name", 2: "Create Date", 3: "Last Build Date"}
SORT_DIRECTIONS: Dict[int, str] = {1: "ASC", 2: "DESC"}


def _trim_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of the profile without excluded keys."""
    out = dict(profile)
    for key in EXCLUDED_PROFILE_KEYS:
        out.pop(key, None)
    return out


@mcp.tool()
async def get_build_profiles(
    page: Optional[int] = None,
    size: Optional[int] = None,
    search: Optional[str] = None,
    platform: Optional[List[int]] = None,
    last_build_status: Optional[List[int]] = None,
    repository_source: Optional[List[int]] = None,
    sort: Optional[int] = None,
    sort_direction: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Get build profiles for the current organization (paginated).

    Returns a list of build profiles with their IDs, names, platform types,
    repository information, build status, and configuration details.
    Optionally filter by profile name using the search parameter, and/or by
    platform, last build status, and repository source. Optionally sort.

    Args:
        page: Page number (1-based). Default: 1.
        size: Page size (1-100). Default: 25. Values above 100 are capped at 100.
        search: Optional search term to filter profiles (case-insensitive partial match on
                profile name; the API's search may also match other profile fields).
                For example, search="iOS" will return profiles with "iOS" in their name,
                and possibly others matching on a different field.
        platform: Optional list of platform codes to filter by. Allowed values:
            1=iOS, 2=Android.
        last_build_status: Optional list of last build status codes to filter by. Allowed values:
            0=Success, 1=Failed, 2=Canceled, 3=Timeout, 90=Waiting, 91=Running.
        repository_source: Optional list of repository source codes to filter by. Allowed values:
            1=GitHub, 2=Bitbucket, 3=GitLab, 4=Azure DevOps, 6=Public Repository,
            7=Private Repository, 8=SSH.
        sort: Optional sort field code. Allowed values: 1=Profile Name, 2=Create Date,
            3=Last Build Date.
        sort_direction: Optional sort direction code. Allowed values: 1=ASC, 2=DESC.

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (list of build profile objects), meta (count, page,
          page_size, search_term, platform, last_build_status, repository_source, sort, sort_direction).
        - Error: success (false), error (tool, type, message, details).
        Profile objects exclude connectionEnvironmentKey and webhookSecret.

    Examples:
        Get first page (default size 25): get_build_profiles()
        Get page 2 with 10 items: get_build_profiles(page=2, size=10)
        Search for iOS profiles: get_build_profiles(search="iOS")
        Filter by platform and last build status: get_build_profiles(platform=[1], last_build_status=[1])
        Sort by create date descending: get_build_profiles(sort=2, sort_direction=2)
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
            validate_enum_list(last_build_status, LAST_BUILD_STATUSES, "last_build_status"),
            validate_enum_list(repository_source, REPOSITORY_SOURCES, "repository_source"),
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
        if last_build_status is not None:
            params["lastBuildStatus"] = last_build_status
        if repository_source is not None:
            params["repositorySource"] = repository_source
        if sort is not None:
            params["sort"] = sort
        if sort_direction is not None:
            params["sortDirection"] = sort_direction

        logger.debug(
            f"Fetching build profiles - page: {page}, size: {size}, search: {search}, "
            f"platform: {platform}, last_build_status: {last_build_status}, "
            f"repository_source: {repository_source}, sort: {sort}, sort_direction: {sort_direction}"
        )

        api_client = ApiClient()
        response = await api_client.get("/build/v2/profiles", params=params)

        # Support both raw list and wrapper (e.g. {"data": [...], "pagination": ..., "summary": ...})
        if isinstance(response, list):
            profiles_raw = response
        elif isinstance(response, dict):
            profiles_raw = response.get("data") or response.get("items") or response.get("profiles") or []
            if not isinstance(profiles_raw, list):
                profiles_raw = []
        else:
            profiles_raw = []
        response = profiles_raw

        data = [_trim_profile(p) for p in response]
        count = len(data)

        if search:
            logger.info(f"Successfully retrieved {count} build profiles matching '{search}' (page {page})")
        else:
            logger.info(f"Successfully retrieved {count} build profiles (page {page})")

        meta = {
            "count": count,
            "page": page,
            "page_size": size,
            "search_term": search,
            "platform": platform,
            "last_build_status": last_build_status,
            "repository_source": repository_source,
            "sort": sort,
            "sort_direction": sort_direction,
        }

        return success_response(data=data, meta=meta)

    except Exception as e:
        logger.error(f"Failed to get build profiles: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
