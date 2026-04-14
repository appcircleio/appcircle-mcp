"""
Get distribution sent report tool (daily usage for distributed app sharing).
"""

from typing import Dict, Any, Optional, Literal

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...schemas.responses import success_response

TOOL_NAME = "get_distribution_sent_report"

OSType = Literal["ios", "android"]


@mcp.tool()
async def get_distribution_sent_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: Optional[int] = None,
    size: Optional[int] = None,
    profile_name: Optional[str] = None,
    os: Optional[OSType] = None,
    organization_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get daily usage report for distributed app sharing.

    Retrieves paginated daily usage data for app sharing (distribute-sent) via
    distribution profiles. Called without start_date and end_date, returns
    every item in the report. Supports filtering by profile, OS, and organization.

    IMPORTANT: Results are paginated by default to prevent token limit issues.
    Default page size is 50 items. Use page parameter to retrieve additional results.

    Args:
        start_date: Optional start date (format: "YYYY-MM-DD", e.g., "2024-01-01")
        end_date: Optional end date (format: "YYYY-MM-DD", e.g., "2024-12-31")
        page: Page number (starts from 1, default: 1)
        size: Items per page (1-100, default: 50)
        profile_name: Filter by distribution profile name
        os: Filter by OS ("ios" or "android")
        organization_id: Filter by organization UUID

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (list of daily usage records), meta (count, page, page_size, total_count, total_pages, has_more, next_page, filters).
        - Error: success (false), error (tool, type, message, details).

    Examples:
        Get all distribution sent report (no date filter):
            get_distribution_sent_report()

        Get report for last month:
            get_distribution_sent_report(
                start_date="2024-11-01",
                end_date="2024-11-30"
            )

        Filter by profile and OS:
            get_distribution_sent_report(
                start_date="2024-01-01",
                end_date="2024-12-31",
                profile_name="Internal Testing",
                os="ios"
            )
    """
    try:
        page = page if page is not None else 1
        size = size if size is not None else 50

        if size > 100:
            logger.warning(f"Requested size {size} exceeds maximum 100, using 100")
            size = 100

        logger.debug(
            f"Fetching distribution sent report - "
            f"start_date: {start_date}, end_date: {end_date}, "
            f"page: {page}, size: {size}, "
            f"profile_name: {profile_name}, os: {os}, organization_id: {organization_id}"
        )

        params = {
            "page": str(page),
            "size": str(size),
        }
        if start_date is not None:
            params["startDate"] = start_date
        if end_date is not None:
            params["endDate"] = end_date
        if profile_name is not None:
            params["profileName"] = profile_name
        if os is not None:
            params["os"] = os
        if organization_id is not None:
            params["organizationId"] = organization_id

        api_client = ApiClient()
        response = await api_client.get("/report/v2/distribute-sent", params=params)

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
            f"Successfully retrieved {len(data)} distribution sent report records "
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
                "profile_name": profile_name,
                "os": os,
                "organization_id": organization_id,
            },
        }
        return success_response(data=data, meta=meta)

    except Exception as e:
        logger.error(f"Failed to get distribution sent report: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
