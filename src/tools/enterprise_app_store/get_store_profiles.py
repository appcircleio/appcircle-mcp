"""Get enterprise app store profiles tool."""

from typing import Dict, Any, Optional

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...schemas.responses import success_response

TOOL_NAME = "get_store_profiles"


@mcp.tool()
async def get_store_profiles(
    page: Optional[int] = None,
    size: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Get enterprise app store profiles for the current organization (paginated).

    Returns a list of enterprise app store profiles with their IDs, names,
    and configuration details. This tool does not support search filtering.

    Args:
        page: Page number (1-based). Default: 1.
        size: Page size (1-100). Default: 25. Values above 100 are capped at 100.

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (list of enterprise app store profile objects), meta (count, page, page_size).
        - Error: success (false), error (tool, type, message, details).

    Examples:
        Get first page (default size 25): get_store_profiles()
        Get page 2 with 10 items: get_store_profiles(page=2, size=10)
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

        logger.debug(f"Fetching enterprise app store profiles - page: {page}, size: {size}")

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
        }

        return success_response(data=data, meta=meta)

    except Exception as e:
        logger.error(f"Failed to get enterprise app store profiles: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
