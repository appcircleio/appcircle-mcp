"""Get build activity log tool."""

from typing import Any, Dict, Optional

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...core.validation import validate_date_format
from ...schemas.responses import success_response

TOOL_NAME = "get_build_activity_log"

ENDPOINT = "/report/v1/build/activity"

# Build activity action codes, as seen in the Appcircle dashboard's activity log
# filter (not documented in the API's Swagger spec).
BUILD_ACTIVITY_ACTIONS: Dict[int, str] = {
    1: "Profile created",
    2: "Profile deleted",
    3: "Profile updated",
    4: "Profile renamed",
    5: "Profile pinned",
    6: "Profile unpinned",
    7: "Profile connection revoked",
    50: "Configuration created",
    51: "Configuration deleted",
    52: "Configuration saved",
    53: "Configuration renamed",
    54: "Configuration cloned",
    55: "Configuration uploaded",
    100: "Build workflow created",
    101: "Build workflow saved",
    102: "Build workflow renamed",
    103: "Build workflow cloned",
    104: "Build workflow deleted",
    105: "Build workflow uploaded",
    120: "Build trigger updated",
    200: "Connection established",
    201: "Connection added",
    202: "Connection renewed",
    203: "Connection removed",
    204: "Connection revoked",
    205: "Connection personal access token modified",
    206: "Connection personal access token removed",
    207: "Connection personal access token added",
    250: "Repository connected",
    251: "Repository disconnected",
    252: "Repository refreshed",
    253: "Repository owner changed",
    300: "Build env. group created",
    301: "Build env. group renamed",
    302: "Build env. group cloned",
    303: "Build env. group deleted",
    320: "Build env. variable created",
    321: "Build env. variable deleted",
    322: "Build env. variable updated",
    323: "CodePush app created",
    324: "CodePush deployment created",
    325: "CodePush app deleted",
    326: "CodePush deployment channel deleted",
    327: "CodePush release published",
    328: "CodePush release disabled",
    329: "CodePush release enabled",
    330: "CodePush release rolled back",
    331: "CodePush rollout updated",
    332: "CodePush app renamed",
    333: "CodePush deployment channel renamed",
    334: "CodePush release updated",
    335: "CodePush release promoted",
    360: "Builds cleanup",
    361: "Build env. group exported",
    362: "Build env. variable imported",
    370: "Build env. variables shared with sub-organization",
    371: "Build env. variables unshared with sub-organization",
    372: "Build env. variables shared with all sub-organizations",
    373: "Build env. variables unshared with all sub-organizations",
}


@mcp.tool()
async def get_build_activity_log(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: Optional[int] = None,
    size: Optional[int] = None,
    organization_id: Optional[str] = None,
    platform: Optional[int] = None,
    email: Optional[str] = None,
    profile_name: Optional[str] = None,
    action: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Get the build activity log, optionally filtered by date range and other parameters.

    Retrieves paginated build activity records (workflow/profile changes, CodePush
    releases, etc.), each with the acting user, profile, action code, and a
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
        platform: Filter by platform type (integer code, e.g. 0=Android, 1=iOS)
        email: Filter by acting user's email
        profile_name: Filter by build profile name
        action: Filter by activity action code. See BUILD_ACTIVITY_ACTIONS for the full
            mapping, e.g. 1=Profile created, 101=Build workflow saved, 322=Build env.
            variable updated, 327=CodePush release published.

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (list of activity log records), meta (count, page, page_size, total_count, total_pages, has_more, next_page, filters).
        - Error: success (false), error (tool, type, message, details). type is validation_error
          when start_date/end_date is malformed (not YYYY-MM-DD) or start_date is after end_date.

    Examples:
        Get all build activity (no date filter):
            get_build_activity_log()

        Get build activity for a date range:
            get_build_activity_log(start_date="2026-06-01", end_date="2026-06-30")

        Filter by profile and acting user:
            get_build_activity_log(profile_name="RN084iOS", email="user@example.com")
    """
    try:
        date_error = validate_date_format(start_date, "start_date") or validate_date_format(end_date, "end_date")
        if date_error is not None:
            raise ValueError(date_error)
        if start_date is not None and end_date is not None and start_date > end_date:
            raise ValueError(f"start_date ({start_date}) must be <= end_date ({end_date})")

        if action is not None and action not in BUILD_ACTIVITY_ACTIONS:
            logger.warning(
                f"action {action} not in known BUILD_ACTIVITY_ACTIONS set; passing to API anyway"
            )

        page = 1 if page is None or page < 1 else page
        size = 50 if size is None else size

        if size > 100:
            logger.warning(f"Requested size {size} exceeds maximum 100, using 100")
            size = 100
        if size < 1:
            size = 1

        logger.debug(
            f"Fetching build activity log - "
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
            params["organizationId"] = organization_id
        if platform is not None:
            params["platform"] = str(platform)
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
            f"Successfully retrieved {len(data)} build activity log records "
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
        logger.error(f"Failed to get build activity log: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
