"""
Get enterprise app store app usage report tool.
"""

from typing import Dict, Any, Optional

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...schemas.responses import success_response

TOOL_NAME = "get_enterprise_app_store_app_usage_report"


@mcp.tool()
async def get_enterprise_app_store_app_usage_report(
    start_date: str,
    end_date: str,
    page: Optional[int] = None,
    size: Optional[int] = None,
    organization_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get app usage report for enterprise app store.

    Retrieves paginated daily app usage data for the enterprise app store.
    start_date and end_date are required. Supports optional filter by organization.

    IMPORTANT: Results are paginated by default to prevent token limit issues.
    Default page size is 50 items. Use page parameter to retrieve additional results.

    Args:
        start_date: Start date (format: "YYYY-MM-DD", e.g., "2024-01-01")
        end_date: End date (format: "YYYY-MM-DD", e.g., "2024-12-31")
        page: Page number (starts from 1, default: 1)
        size: Items per page (1-100, default: 50)
        organization_id: Optional filter by organization UUID

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (list of app usage records), meta (count, page, page_size, total_count, total_pages, has_more, next_page, filters).
        - Error: success (false), error (tool, type, message, details).

    Examples:
        Get app usage for last month:
            get_enterprise_app_store_app_usage_report(
                start_date="2024-11-01",
                end_date="2024-11-30"
            )

        Filter by organization:
            get_enterprise_app_store_app_usage_report(
                start_date="2024-01-01",
                end_date="2024-12-31",
                organization_id="49ddc35d-85e8-4898-a4f7-496b63660db4"
            )
    """
    try:
        page = page if page is not None else 1
        size = size if size is not None else 50

        if size > 100:
            logger.warning(f"Requested size {size} exceeds maximum 100, using 100")
            size = 100

        logger.debug(
            f"Fetching enterprise app store app usage report - "
            f"start_date: {start_date}, end_date: {end_date}, "
            f"page: {page}, size: {size}, organization_id: {organization_id}"
        )

        params = {
            "startDate": start_date,
            "endDate": end_date,
            "page": str(page),
            "size": str(size),
        }
        if organization_id is not None:
            params["organizationId"] = organization_id

        api_client = ApiClient()
        response = await api_client.get("/store-report/v2/app-usage", params=params)

        data = response.get("data", [])
        pagination_info = response.get("pagination", {})

        current_page = pagination_info.get("page", page)
        per_page = pagination_info.get("perPage", size)
        total_count = pagination_info.get("totalCount", len(data))
        total_pages = pagination_info.get("pageCount", 1)
        enable_next = pagination_info.get("enableNext", False)

        has_more = enable_next or (current_page < total_pages)
        next_page = current_page + 1 if has_more else None

        logger.info(
            f"Successfully retrieved {len(data)} enterprise app store app usage records "
            f"(page {current_page}/{total_pages}, total: {total_count})"
        )
        if has_more:
            logger.info(f"More results available on page {next_page}")

        meta = {
            "count": len(data),
            "page": current_page,
            "page_size": per_page,
            "total_count": total_count,
            "total_pages": total_pages,
            "has_more": has_more,
            "next_page": next_page,
            "filters": {
                "start_date": start_date,
                "end_date": end_date,
                "organization_id": organization_id,
            },
        }
        return success_response(data=data, meta=meta)

    except Exception as e:
        logger.error(f"Failed to get enterprise app store app usage report: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
