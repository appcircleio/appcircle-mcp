"""Get signing activity log tool."""

from typing import Any, Dict, Optional

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...core.validation import validate_date_format
from ...schemas.responses import success_response

TOOL_NAME = "get_signing_activity_log"

ENDPOINT = "/report/v2/sign/activity"

# Signing activity action codes, as seen in the Appcircle dashboard's activity log
# filter (not documented in the API's Swagger spec).
SIGNING_ACTIVITY_ACTIONS: Dict[int, str] = {
    5: "P12 added",
    6: "CSR generated",
    7: "Certificate uploaded",
    8: "Certificate expiring soon",
    9: "Certificate downloaded",
    10: "Certificate deleted",
    11: "Provisioning profile deleted",
    12: "Provisioning profile added",
    13: "Provisioning profile renewed",
    14: "Provisioning profile downloaded",
    15: "Provisioning profile expiring soon",
    16: "Keystore created",
    17: "Keystore uploaded",
    18: "Keystore deleted",
    19: "Keystore downloaded",
    20: "Keystore expiring soon",
    21: "App Store bundle id created",
    22: "App Store bundle id deleted",
    23: "Bundle id created on App Store",
    24: "Bundle id updated on App Store",
    25: "Tester devices added",
    26: "Tester device deleted",
    27: "Tester device invitation deleted",
    28: "Device provisioned",
    29: "Device provisioning failed",
    30: "Device registration link sent",
    31: "Device registered",
    32: "Multiple devices registered",
    33: "Multiple device registration failed",
    34: "App Store authentication failed",
    35: "App Store device synced",
    36: "App Store device sync cancelled",
    37: "Multiple devices added to App Store",
    38: "Apple devices updated",
    39: "Apple device update failed",
    40: "Multiple apple devices updated",
    41: "Multiple apple devices update failed",
    42: "App Store device sync requested",
    43: "Keystore shared with sub-organizations",
    44: "Keystore unshared with sub-organizations",
    45: "Keystore shared with all sub-organizations",
    46: "Keystore unshared with all sub-organizations",
    47: "Provisioning profile shared with sub-organizations",
    48: "Provisioning profile unshared with sub-organizations",
    49: "Provisioning profiles shared with all sub-organizations",
    50: "Provisioning profiles unshared with all sub-organizations",
    51: "Certificate shared with sub-organizations",
    52: "Certificate unshared with sub-organizations",
    53: "Certificate shared with all sub-organizations",
    54: "Certificate unshared with all sub-organizations",
    55: "Certificate revoked",
    56: "Certificate renewed",
}


@mcp.tool()
async def get_signing_activity_log(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: Optional[int] = None,
    size: Optional[int] = None,
    organization_id: Optional[str] = None,
    platform: Optional[str] = None,
    email: Optional[str] = None,
    action: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Get the signing activity log, optionally filtered by date range and other parameters.

    Retrieves paginated signing activity records (e.g. certificate/provisioning
    profile/keystore expiry notices), each with the affected signing identity,
    an action code, and a human-readable description. Called without start_date
    and end_date, returns every item in the log.

    IMPORTANT: Results are paginated by default to prevent token limit issues.
    Default page size is 50 items. Use page parameter to retrieve additional results.

    Args:
        start_date: Optional start date (format: "YYYY-MM-DD"). Must be <= end_date if both are given.
        end_date: Optional end date (format: "YYYY-MM-DD").
        page: Page number (starts from 1, default: 1)
        size: Items per page (1-100, default: 50)
        organization_id: Filter by organization UUID
        platform: Filter by platform (e.g. "iOS", "Android", matching the response's platformType)
        email: Filter by acting user's email
        action: Filter by activity action code. See SIGNING_ACTIVITY_ACTIONS for the full
            mapping, e.g. 8=Certificate expiring soon, 15=Provisioning profile expiring
            soon, 20=Keystore expiring soon.

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (list of signing activity log records), meta (count, page, page_size, total_count, total_pages, has_more, next_page, filters).
        - Error: success (false), error (tool, type, message, details). type is validation_error
          when start_date/end_date is malformed (not YYYY-MM-DD) or start_date is after end_date.

    Examples:
        Get all signing activity (no date filter):
            get_signing_activity_log()

        Get signing activity for a date range:
            get_signing_activity_log(start_date="2026-06-01", end_date="2026-06-30")

        Filter by platform:
            get_signing_activity_log(platform="iOS")
    """
    try:
        date_error = validate_date_format(start_date, "start_date") or validate_date_format(end_date, "end_date")
        if date_error is not None:
            raise ValueError(date_error)
        if start_date is not None and end_date is not None and start_date > end_date:
            raise ValueError(f"start_date ({start_date}) must be <= end_date ({end_date})")

        if action is not None and action not in SIGNING_ACTIVITY_ACTIONS:
            logger.warning(
                f"action {action} not in known SIGNING_ACTIVITY_ACTIONS set; passing to API anyway"
            )

        page = 1 if page is None or page < 1 else page
        size = 50 if size is None else size

        if size > 100:
            logger.warning(f"Requested size {size} exceeds maximum 100, using 100")
            size = 100
        if size < 1:
            size = 1

        logger.debug(
            f"Fetching signing activity log - "
            f"start_date: {start_date}, end_date: {end_date}, "
            f"page: {page}, size: {size}, "
            f"organization_id: {organization_id}, platform: {platform}, "
            f"email: {email}, action: {action}"
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
            params["organization"] = organization_id
        if platform is not None:
            params["platform"] = platform
        if email is not None:
            params["email"] = email
        if action is not None:
            params["action"] = str(action)

        api_client = ApiClient()
        response = await api_client.get(ENDPOINT, params=params)

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
            f"Successfully retrieved {len(data)} signing activity log records "
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
                "platform": platform,
                "email": email,
                "action": action,
            },
        }
        return success_response(data=data, meta=meta)

    except Exception as e:
        logger.error(f"Failed to get signing activity log: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
