"""Get publish activity log tool."""

from typing import Any, Dict, Optional

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...core.validation import validate_date_format
from ...schemas.responses import success_response

TOOL_NAME = "get_publish_activity_log"

ENDPOINT = "/report/v2/publish/activity"

# Publish activity action codes, as seen in the Appcircle dashboard's activity log
# filter (not documented in the API's Swagger spec).
PUBLISH_ACTIVITY_ACTIONS: Dict[int, str] = {
    1: "Publish flow updated",
    2: "Publish updated",
    3: "Publish step updated",
    4: "Publish step failed",
    6: "Publish step succeeded",
    7: "Publishing restarted",
    8: "Publish item archived",
    10: "Publishing stopped",
    11: "Publishing succeeded",
    12: "No artifact to publish",
    13: "Publishing failed",
    14: "Publish step starting",
    15: "Publish step started",
    16: "Publish step cancelled",
    18: "Publish cancelled",
    20: "Publish profile created",
    21: "App version uploaded",
    22: "App version created",
    23: "Publish profile deleted",
    24: "App version deleted",
    25: "Metadata file deleted",
    26: "Metadata file deleting",
    27: "Metadata file deleting cancelled",
    28: "Metadata importing",
    29: "Metadata importing cancelled",
    30: "Metadata imported",
    31: "Metadata uploading",
    32: "Metadata updated",
    33: "Metadata uploaded",
    34: "Metadata uploading cancelled",
    35: "Re-sign starting",
    36: "Re-sign started",
    37: "Re-sign starting cancelled",
    38: "Re-sign succeeded",
    39: "Re-sign failed",
    40: "Re-sign cancelled",
    41: "Marked as release candidate",
    42: "Unmarked as release candidate",
    43: "Release note updated",
    44: "App info update failed",
    45: "Some app info updates failed",
    46: "App info updated on store",
    47: "App version rejected",
    48: "Review submission cancelled",
    49: "Play Store release updated",
    50: "Play Store release failed",
    51: "Publish profile updated",
    52: "Auto re-sign configurations updated",
    54: "App Store release succeeded",
    55: "Play Store manual rollout succeeded",
    56: "Play Store manual rollout failed",
    57: "Play Store auto rollout progressed",
    58: "Play Store auto rollout completed",
    59: "Play Store auto rollout failed",
    60: "Play Store rollout halted",
    61: "Play Store rollout resumed",
    62: "Re-sign timed out",
    100: "Publish env. group created",
    101: "Publish env. group renamed",
    102: "Publish env. group cloned",
    103: "Publish env. group deleted",
    120: "Publish env. variable created",
    121: "Publish env. variable deleted",
    122: "Publish env. variable updated",
    123: "App Store beta submission succeeded",
    161: "Publish env. variable exported",
    163: "Publish env. variable imported",
    170: "Publish env. variable shared with sub-organizations",
    171: "Publish env. variable unshared with sub-organizations",
    172: "Publish env. variables shared with all sub-organizations",
    173: "Publish env. variables unshared with all sub-organizations",
    180: "Publish app release information updated",
    181: "Publish app release information update failed",
    182: "Store status checked",
}


@mcp.tool()
async def get_publish_activity_log(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: Optional[int] = None,
    size: Optional[int] = None,
    organization_id: Optional[str] = None,
    platform: Optional[str] = None,
    email: Optional[str] = None,
    profile_name: Optional[str] = None,
    action: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Get the publish activity log, optionally filtered by date range and other parameters.

    Retrieves paginated publish activity records (re-sign, publish flow events,
    etc.), each with the acting user, publish profile, an action code, and a
    human-readable description. Called without start_date and end_date, returns
    every item in the log.

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
        profile_name: Filter by publish profile name
        action: Filter by activity action code. See PUBLISH_ACTIVITY_ACTIONS for the full
            mapping, e.g. 13=Publishing failed, 39=Re-sign failed, 47=App version rejected.

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (list of publish activity log records), meta (count, page, page_size, total_count, total_pages, has_more, next_page, filters).
        - Error: success (false), error (tool, type, message, details). type is validation_error
          when start_date/end_date is malformed (not YYYY-MM-DD) or start_date is after end_date.

    Examples:
        Get all publish activity (no date filter):
            get_publish_activity_log()

        Get publish activity for a date range:
            get_publish_activity_log(start_date="2026-06-01", end_date="2026-06-30")

        Filter by profile and platform:
            get_publish_activity_log(profile_name="HelloWorldApp", platform="iOS")
    """
    try:
        date_error = validate_date_format(start_date, "start_date") or validate_date_format(end_date, "end_date")
        if date_error is not None:
            raise ValueError(date_error)
        if start_date is not None and end_date is not None and start_date > end_date:
            raise ValueError(f"start_date ({start_date}) must be <= end_date ({end_date})")

        if action is not None and action not in PUBLISH_ACTIVITY_ACTIONS:
            logger.warning(
                f"action {action} not in known PUBLISH_ACTIVITY_ACTIONS set; passing to API anyway"
            )

        page = 1 if page is None or page < 1 else page
        size = 50 if size is None else size

        if size > 100:
            logger.warning(f"Requested size {size} exceeds maximum 100, using 100")
            size = 100
        if size < 1:
            size = 1

        logger.debug(
            f"Fetching publish activity log - "
            f"start_date: {start_date}, end_date: {end_date}, "
            f"page: {page}, size: {size}, "
            f"organization_id: {organization_id}, platform: {platform}, "
            f"email: {email}, profile_name: {profile_name}, action: {action}"
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
        if profile_name is not None:
            params["profileName"] = profile_name
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
            f"Successfully retrieved {len(data)} publish activity log records "
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
                "profile_name": profile_name,
                "action": action,
            },
        }
        return success_response(data=data, meta=meta)

    except Exception as e:
        logger.error(f"Failed to get publish activity log: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
