"""Get publish profiles tool."""

from typing import Dict, Any, Optional, Literal

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...schemas.responses import error_response, success_response

TOOL_NAME = "get_publish_profiles"

PlatformType = Literal["ios", "android"]

# Flow status enum: 0=Success, 1=Failed, 2=Canceled, 3=Timeout, 90=Waiting, 91=Running,
# 92=Completing, 99=Unknown, 200=NotStarted, 201=Stopped, 202=InProgress, 203=AwaitingResponse
VALID_FLOW_STATUSES = frozenset({0, 1, 2, 3, 90, 91, 92, 99, 200, 201, 202, 203})


def _build_meta_from_pagination(
    pagination: Optional[Dict[str, Any]], page: int, size: int, platform_type: str, flow_status: Optional[int]
) -> Dict[str, Any]:
    """Build meta dict from API pagination and request params."""
    base = {
        "platform_type": platform_type,
        "page": page,
        "page_size": size,
        "flow_status": flow_status,
    }
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
async def get_publish_profiles(
    platform_type: PlatformType,
    page: Optional[int] = None,
    size: Optional[int] = None,
    flow_status: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Get publish profiles for the current organization for a given platform type (paginated).

    Returns a list of publish profiles with their IDs, names, app versions, version information,
    flow status information, and profile settings. Optionally filter by flow status.

    Args:
        platform_type: Platform type of publish profiles ("ios" or "android").
        page: Page number (1-based). Default: 1.
        size: Page size (1-100). Default: 25. Values above 100 are capped at 100.
        flow_status: Optional flow status code to filter by (single value).
            Allowed values: 0=Success, 1=Failed, 2=Canceled, 3=Timeout, 90=Waiting, 91=Running,
            92=Completing, 99=Unknown, 200=NotStarted, 201=Stopped, 202=InProgress, 203=AwaitingResponse.

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (list of publish profile objects), meta (page, page_size, platform_type, flow_status, pagination metadata).
        - Error: success (false), error (tool, type, message, details).

    Examples:
        Get first page of iOS profiles: get_publish_profiles(platform_type="ios")
        Get page 2 with 10 items: get_publish_profiles(platform_type="android", page=2, size=10)
        Filter by flow status: get_publish_profiles(platform_type="ios", flow_status=0)
    """
    try:
        page = 1 if page is None or page < 1 else page
        size = 25 if size is None else size
        if size > 100:
            logger.warning(f"Requested size {size} exceeds maximum 100, using 100")
            size = 100
        if size < 1:
            size = 1

        if flow_status is not None and flow_status not in VALID_FLOW_STATUSES:
            return error_response(
                tool=TOOL_NAME,
                type="validation_error",
                message=f"Invalid flow_status: {flow_status}. Allowed values: {sorted(VALID_FLOW_STATUSES)}",
            )

        params = {
            "page": str(page),
            "size": str(size),
        }
        if flow_status is not None and flow_status in VALID_FLOW_STATUSES:
            params["flowStatus"] = str(flow_status)

        logger.debug(
            f"Fetching publish profiles - platform_type: {platform_type}, page: {page}, size: {size}, flow_status: {flow_status}"
        )

        api_client = ApiClient()
        response = await api_client.get(f"/publish/v2/profiles/{platform_type}", params=params)

        if isinstance(response, list):
            profiles_raw = response
            pagination = None
        elif isinstance(response, dict):
            profiles_raw = response.get("data") or response.get("items") or response.get("profiles") or []
            if not isinstance(profiles_raw, list):
                profiles_raw = []
            pagination = response.get("pagination")
        else:
            profiles_raw = []
            pagination = None

        data = list(profiles_raw)
        count = len(data)
        meta = _build_meta_from_pagination(pagination, page, size, platform_type, flow_status)
        meta["count"] = count

        logger.info(
            f"Successfully retrieved {count} publish profiles for '{platform_type}' (page {page})"
        )

        return success_response(data=data, meta=meta)

    except Exception as e:
        logger.error(f"Failed to get publish profiles: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
