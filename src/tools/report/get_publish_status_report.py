"""
Get publish status report tool.
"""

from typing import Dict, Any, Optional

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...schemas.responses import success_response

TOOL_NAME = "get_publish_status_report"

# PublishStatus: 0=Success, 1=Failed, 2=Canceled, 3=Timeout, 90=Waiting, 91=Running,
# 92=Completing, 99=Unknown, 200=NotStarted, 201=Stopped, 202=InProgress, 203=AwaitingResponse
VALID_PUBLISH_STATUSES = frozenset(
    {0, 1, 2, 3, 90, 91, 92, 99, 200, 201, 202, 203}
)


@mcp.tool()
async def get_publish_status_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: Optional[int] = None,
    size: Optional[int] = None,
    app_name: Optional[str] = None,
    organization_id: Optional[str] = None,
    status: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Get publish status report, optionally filtered by date range and other parameters.

    Retrieves paginated publish status data. Called without start_date and end_date,
    returns every item in the report. Supports filtering by app name, organization, and status.

    IMPORTANT: Results are paginated by default to prevent token limit issues.
    Default page size is 50 items. Use page parameter to retrieve additional results.

    Args:
        start_date: Optional start date (format: "YYYY-MM-DD", e.g., "2024-01-01")
        end_date: Optional end date (format: "YYYY-MM-DD", e.g., "2024-12-31")
        page: Page number (starts from 1, default: 1)
        size: Items per page (1-100, default: 50)
        app_name: Filter by app name
        organization_id: Filter by organization UUID
        status: Filter by publish status. Allowed: 0=Success, 1=Failed, 2=Canceled,
            3=Timeout, 90=Waiting, 91=Running, 92=Completing, 99=Unknown,
            200=NotStarted, 201=Stopped, 202=InProgress, 203=AwaitingResponse

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (list of publish status records), meta (count, page, page_size, total_count, total_pages, has_more, next_page, filters).
        - Error: success (false), error (tool, type, message, details).

    Examples:
        Get all publish status report (no date filter):
            get_publish_status_report()

        Get report for last month:
            get_publish_status_report(
                start_date="2024-11-01",
                end_date="2024-11-30"
            )

        Filter by status (success only):
            get_publish_status_report(
                start_date="2024-01-01",
                end_date="2024-12-31",
                status=0
            )
    """
    try:
        page = page if page is not None else 1
        size = size if size is not None else 50

        if size > 100:
            logger.warning(f"Requested size {size} exceeds maximum 100, using 100")
            size = 100

        if status is not None and status not in VALID_PUBLISH_STATUSES:
            logger.warning(
                f"status {status} not in allowed set {sorted(VALID_PUBLISH_STATUSES)}; passing to API anyway"
            )

        logger.debug(
            f"Fetching publish status report - "
            f"start_date: {start_date}, end_date: {end_date}, "
            f"page: {page}, size: {size}, "
            f"app_name: {app_name}, organization_id: {organization_id}, status: {status}"
        )

        params = {
            "page": str(page),
            "size": str(size),
        }
        if start_date is not None:
            params["startDate"] = start_date
        if end_date is not None:
            params["endDate"] = end_date
        if app_name is not None:
            params["appName"] = app_name
        if organization_id is not None:
            params["organizationId"] = organization_id
        if status is not None:
            params["status"] = str(status)

        api_client = ApiClient()
        response = await api_client.get("/report/v1/publish/status", params=params)

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
            f"Successfully retrieved {len(data)} publish status report records "
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
                "app_name": app_name,
                "organization_id": organization_id,
                "status": status,
            },
        }
        return success_response(data=data, meta=meta)

    except Exception as e:
        logger.error(f"Failed to get publish status report: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
