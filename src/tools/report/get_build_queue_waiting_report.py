"""Get build queue waiting report tool."""

from typing import Any, Dict, Optional

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...core.validation import validate_date_format
from ...schemas.responses import success_response

TOOL_NAME = "get_build_queue_waiting_report"

ENDPOINT = "/report/v1/build/queue-waiting"


@mcp.tool()
async def get_build_queue_waiting_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: Optional[int] = None,
    size: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Get the build queue waiting report, optionally filtered by date range.

    Retrieves paginated queue-wait records per build (machine plan, OS,
    trigger type, build profile/branch/commit, and queue wait duration).
    Called without start_date and end_date, returns every item in the report.

    IMPORTANT: On this endpoint, `buildDuration` means queue wait time in
    minutes, not execution time -- unlike the same field name on
    get_build_history_report's /report/v2/build.

    IMPORTANT: Results are paginated by default to prevent token limit issues.
    Default page size is 50 items. Use page parameter to retrieve additional results.

    Args:
        start_date: Optional start date (format: "YYYY-MM-DD"). Must be <= end_date if both are given.
        end_date: Optional end date (format: "YYYY-MM-DD").
        page: Page number (starts from 1, default: 1)
        size: Items per page (1-100, default: 50)

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (list of queue-wait records), meta (count, page,
          page_size, total_count, total_pages, has_more, next_page, filters, summary --
          org-wide queue wait totals by machine plan (standard/velocity/ultra) for the
          whole filtered query, taken from the API's own summary field, or None if absent).
        - Error: success (false), error (tool, type, message, details). type is validation_error
          when start_date/end_date is malformed (not YYYY-MM-DD) or start_date is after end_date.

    Examples:
        Get all queue-wait records (no date filter):
            get_build_queue_waiting_report()

        Get queue-wait records for a date range:
            get_build_queue_waiting_report(start_date="2026-06-01", end_date="2026-06-30")
    """
    try:
        date_error = validate_date_format(start_date, "start_date") or validate_date_format(end_date, "end_date")
        if date_error is not None:
            raise ValueError(date_error)
        if start_date is not None and end_date is not None and start_date > end_date:
            raise ValueError(f"start_date ({start_date}) must be <= end_date ({end_date})")

        page = 1 if page is None or page < 1 else page
        size = 50 if size is None else size

        if size > 100:
            logger.warning(f"Requested size {size} exceeds maximum 100, using 100")
            size = 100
        if size < 1:
            size = 1

        logger.debug(
            f"Fetching build queue waiting report - "
            f"start_date: {start_date}, end_date: {end_date}, page: {page}, size: {size}"
        )

        params = {
            "page": str(page),
            "size": str(size),
        }
        if start_date is not None:
            params["startDate"] = start_date
        if end_date is not None:
            params["endDate"] = end_date

        api_client = ApiClient()
        response = await api_client.get(ENDPOINT, params=params)

        data = response.get("data", [])
        pagination_info = response.get("pagination", {})
        summary = response.get("summary")

        current_page = pagination_info.get("page", page)
        per_page = pagination_info.get("perPage", size)
        total_count = pagination_info.get("totalCount", len(data))
        total_pages = pagination_info.get("pageCount", 1)
        enable_next = pagination_info.get("enableNext", False)

        has_more = enable_next or (current_page < total_pages)
        next_page = current_page + 1 if has_more else None

        logger.info(
            f"Successfully retrieved {len(data)} build queue waiting records "
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
            },
            "summary": summary,
        }
        return success_response(data=data, meta=meta)

    except Exception as e:
        logger.error(f"Failed to get build queue waiting report: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
