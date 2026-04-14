"""
Get signing report tool.
"""

from typing import Dict, Any, Optional, Literal

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...schemas.responses import success_response

TOOL_NAME = "get_signing_report"

# Build status: 0=Success, 1=Failed, 2=Canceled, 3=Timeout, 90=Waiting, 91=Running, 92=Completing, 99=Unknown
VALID_BUILD_STATUSES = frozenset({0, 1, 2, 3, 90, 91, 92, 99})

OSType = Literal["ios", "android"]


@mcp.tool()
async def get_signing_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: Optional[int] = None,
    size: Optional[int] = None,
    organization_id: Optional[str] = None,
    os: Optional[OSType] = None,
    build_status: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Get signing report, optionally filtered by date range and other parameters.

    Retrieves paginated signing report data. Called without start_date and end_date,
    returns every item in the report. Supports filtering by organization, OS, and build status.

    IMPORTANT: Results are paginated by default to prevent token limit issues.
    Default page size is 50 items. Use page parameter to retrieve additional results.

    Args:
        start_date: Optional start date (format: "YYYY-MM-DD", e.g., "2024-01-01")
        end_date: Optional end date (format: "YYYY-MM-DD", e.g., "2024-12-31")
        page: Page number (starts from 1, default: 1)
        size: Items per page (1-100, default: 50)
        organization_id: Filter by organization UUID
        os: Filter by OS ("ios" or "android")
        build_status: Filter by build status. Allowed: 0=Success, 1=Failed, 2=Canceled,
            3=Timeout, 90=Waiting, 91=Running, 92=Completing, 99=Unknown

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (list of signing report records), meta (count, page, page_size, total_count, total_pages, has_more, next_page, filters).
        - Error: success (false), error (tool, type, message, details).

    Examples:
        Get all signing report (no date filter):
            get_signing_report()

        Get signing report for last month:
            get_signing_report(
                start_date="2024-11-01",
                end_date="2024-11-30"
            )

        Filter by OS and build status:
            get_signing_report(
                start_date="2024-01-01",
                end_date="2024-12-31",
                os="ios",
                build_status=0
            )
    """
    try:
        page = page if page is not None else 1
        size = size if size is not None else 50

        if size > 100:
            logger.warning(f"Requested size {size} exceeds maximum 100, using 100")
            size = 100

        if build_status is not None and build_status not in VALID_BUILD_STATUSES:
            logger.warning(
                f"build_status {build_status} not in allowed set {sorted(VALID_BUILD_STATUSES)}; passing to API anyway"
            )

        logger.debug(
            f"Fetching signing report - "
            f"start_date: {start_date}, end_date: {end_date}, "
            f"page: {page}, size: {size}, "
            f"organization_id: {organization_id}, os: {os}, build_status: {build_status}"
        )

        params = {
            "page": str(page),
            "size": str(size),
        }
        if start_date is not None:
            params["startDate"] = start_date
        if end_date is not None:
            params["endDate"] = end_date
        if organization_id is not None:
            params["organizationId"] = organization_id
        if os is not None:
            params["os"] = os
        if build_status is not None:
            params["buildStatus"] = str(build_status)

        api_client = ApiClient()
        response = await api_client.get("/report/v1/sign", params=params)

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
            f"Successfully retrieved {len(data)} signing report records "
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
                "os": os,
                "build_status": build_status,
            },
        }
        return success_response(data=data, meta=meta)

    except Exception as e:
        logger.error(f"Failed to get signing report: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
