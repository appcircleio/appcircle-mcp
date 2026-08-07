"""Get enterprise app store profiles tool."""

from typing import Dict, Any, List, Optional

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...core.validation import validate_enum_list
from ...schemas.responses import error_response, success_response

TOOL_NAME = "get_store_profiles"

# Filter/sort enums, sourced from GET /store/v2/profiles/filters. Real query keys (platformType,
# publishType) differ from the metadata's own field labels (platform, channelStatus).
PLATFORM_TYPES: Dict[int, str] = {1: "iOS", 2: "Android"}
PUBLISH_TYPES: Dict[int, str] = {1: "Published to Beta", 2: "Published to Live"}
SORT_FIELDS: Dict[int, str] = {1: "App Name", 2: "Create Date", 3: "Download Count", 4: "Binary Receive Date"}
SORT_DIRECTIONS: Dict[int, str] = {1: "ASC", 2: "DESC"}


@mcp.tool()
async def get_store_profiles(
    page: Optional[int] = None,
    size: Optional[int] = None,
    platform_type: Optional[List[int]] = None,
    publish_type: Optional[List[int]] = None,
    visibility: Optional[bool] = None,
    sort: Optional[int] = None,
    sort_direction: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Get enterprise app store profiles for the current organization (paginated).

    Returns a list of enterprise app store profiles with their IDs, names,
    and configuration details. This tool does not support search filtering, but
    can filter by platform, publish type, and visibility. Optionally sort.

    Args:
        page: Page number (1-based). Default: 1.
        size: Page size (1-100). Default: 25. Values above 100 are capped at 100.
        platform_type: Optional list of platform codes to filter by. Allowed values:
            1=iOS, 2=Android.
        publish_type: Optional list of publish type codes to filter by. Allowed values:
            1=Published to Beta, 2=Published to Live.
        visibility: Optional filter for whether the profile is publicly listed
            (true=Listed, false=Unlisted).
        sort: Optional sort field code. Allowed values: 1=App Name, 2=Create Date,
            3=Download Count, 4=Binary Receive Date.
        sort_direction: Optional sort direction code. Allowed values: 1=ASC, 2=DESC.

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (list of enterprise app store profile objects), meta (count,
          page, page_size, platform_type, publish_type, visibility, sort, sort_direction).
        - Error: success (false), error (tool, type, message, details).

    Examples:
        Get first page (default size 25): get_store_profiles()
        Get page 2 with 10 items: get_store_profiles(page=2, size=10)
        Filter by platform and publish type: get_store_profiles(platform_type=[1], publish_type=[2])
        Sort by download count descending: get_store_profiles(sort=3, sort_direction=2)
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
            validate_enum_list(platform_type, PLATFORM_TYPES, "platform_type"),
            validate_enum_list(publish_type, PUBLISH_TYPES, "publish_type"),
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
        if platform_type is not None:
            params["platformType"] = platform_type
        if publish_type is not None:
            params["publishType"] = publish_type
        if visibility is not None:
            params["visibility"] = str(visibility).lower()
        if sort is not None:
            params["sort"] = sort
        if sort_direction is not None:
            params["sortDirection"] = sort_direction

        logger.debug(
            f"Fetching enterprise app store profiles - page: {page}, size: {size}, "
            f"platform_type: {platform_type}, publish_type: {publish_type}, visibility: {visibility}, "
            f"sort: {sort}, sort_direction: {sort_direction}"
        )

        api_client = ApiClient()
        response = await api_client.get("/store/v2/profiles", params=params)

        # Support both raw list and wrapper (e.g. {"data": [...], "pagination": ..., ...})
        if isinstance(response, list):
            profiles_raw = response
        elif isinstance(response, dict):
            profiles_raw = response.get("data") or response.get("items") or response.get("profiles") or []
            if not isinstance(profiles_raw, list):
                profiles_raw = []
        else:
            profiles_raw = []

        data = list(profiles_raw)
        count = len(data)

        logger.info(f"Successfully retrieved {count} enterprise app store profiles (page {page})")

        meta = {
            "count": count,
            "page": page,
            "page_size": size,
            "platform_type": platform_type,
            "publish_type": publish_type,
            "visibility": visibility,
            "sort": sort,
            "sort_direction": sort_direction,
        }

        return success_response(data=data, meta=meta)

    except Exception as e:
        logger.error(f"Failed to get enterprise app store profiles: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
