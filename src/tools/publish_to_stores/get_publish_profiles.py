"""Get publish profiles tool."""

from typing import Dict, Any, List, Optional, Literal

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

# Filter/sort enums, sourced from GET /publish/v1/profiles/{platformType}/filters (marketPlaceType and
# storeStatus values differ per platform_type).
MARKET_PLACE_TYPES: Dict[str, Dict[int, str]] = {
    "ios": {0: "Not Available", 1: "App Store Connect", 4: "Intune"},
    "android": {0: "Not Available", 2: "Google Play", 3: "AppGallery", 4: "Intune"},
}
STORE_STATUSES: Dict[str, Dict[str, str]] = {
    "ios": {
        "PROCESSING": "Processing",
        "PROCESSING_EXCEPTION": "Processing Exception",
        "MISSING_EXPORT_COMPLIANCE": "Missing Export Compliance",
        "READY_FOR_BETA_TESTING": "Ready for Beta Testing",
        "IN_BETA_TESTING": "In Beta Testing",
        "EXPIRED": "Expired",
        "READY_FOR_BETA_SUBMISSION": "Ready for Beta Submission",
        "IN_EXPORT_COMPLIANCE_REVIEW": "In Export Compliance Review",
        "WAITING_FOR_BETA_REVIEW": "Waiting for Beta Review",
        "IN_BETA_REVIEW": "In Beta Review",
        "BETA_REJECTED": "Beta Rejected",
        "BETA_APPROVED": "Beta Approved",
        "NOT_AVAILABLE": "Not Available",
        "DEVELOPER_REJECTED": "Developer Rejected",
        "IN_REVIEW": "In Review",
        "INVALID_BINARY": "Invalid Binary",
        "METADATA_REJECTED": "Metadata Rejected",
        "PENDING_APPLE_RELEASE": "Pending Apple Release",
        "PENDING_DEVELOPER_RELEASE": "Pending Developer Release",
        "PREPARE_FOR_SUBMISSION": "Prepare for Submission",
        "PROCESSING_FOR_DISTRIBUTION": "Processing for Distribution",
        "READY_FOR_DISTRIBUTION": "Ready for Distribution",
        "READY_FOR_REVIEW": "Ready for Review",
        "REJECTED": "Rejected",
        "REPLACED_WITH_NEW_VERSION": "Replaced with New Version",
        "WAITING_FOR_EXPORT_COMPLIANCE": "Waiting for Export Compliance",
        "WAITING_FOR_REVIEW": "Waiting for Review",
        "READY_FOR_SALE": "Ready for Sale",
    },
    "android": {
        "NOT_AVAILABLE": "Not Available",
        "DRAFT": "Draft",
        "IN_PROGRESS": "In Progress",
        "HALTED": "Halted",
        "COMPLETED": "Completed",
    },
}
SORT_FIELDS: Dict[int, str] = {1: "Profile Name", 2: "Create Date"}
SORT_DIRECTIONS: Dict[int, str] = {1: "ASC", 2: "DESC"}


def _build_meta_from_pagination(
    pagination: Optional[Dict[str, Any]],
    page: int,
    size: int,
    platform_type: str,
    flow_status: Optional[int],
    market_place_type: Optional[List[int]],
    has_rc_binary: Optional[bool],
    store_status: Optional[List[str]],
    sort: Optional[int],
    sort_direction: Optional[int],
) -> Dict[str, Any]:
    """Build meta dict from API pagination and request params."""
    base = {
        "platform_type": platform_type,
        "page": page,
        "page_size": size,
        "flow_status": flow_status,
        "market_place_type": market_place_type,
        "has_rc_binary": has_rc_binary,
        "store_status": store_status,
        "sort": sort,
        "sort_direction": sort_direction,
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
    market_place_type: Optional[List[int]] = None,
    has_rc_binary: Optional[bool] = None,
    store_status: Optional[List[str]] = None,
    sort: Optional[int] = None,
    sort_direction: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Get publish profiles for the current organization for a given platform type (paginated).

    Returns a list of publish profiles with their IDs, names, app versions, version information,
    flow status information, and profile settings. Optionally filter by flow status, target
    marketplace, release-candidate binary presence, and store status. Optionally sort.

    Args:
        platform_type: Platform type of publish profiles ("ios" or "android").
        page: Page number (1-based). Default: 1.
        size: Page size (1-100). Default: 25. Values above 100 are capped at 100.
        flow_status: Optional flow status code to filter by (single value).
            Allowed values: 0=Success, 1=Failed, 2=Canceled, 3=Timeout, 90=Waiting, 91=Running,
            92=Completing, 99=Unknown, 200=NotStarted, 201=Stopped, 202=InProgress, 203=AwaitingResponse.
        market_place_type: Optional list of target marketplace codes to filter by. Allowed values
            depend on platform_type:
            ios: 0=Not Available, 1=App Store Connect, 4=Intune.
            android: 0=Not Available, 2=Google Play, 3=AppGallery, 4=Intune.
        has_rc_binary: Optional filter for whether the profile has a release-candidate binary.
        store_status: Optional list of store status codes to filter by. Allowed values depend on
            platform_type (many more codes for ios than android, e.g. ios: "IN_REVIEW",
            "READY_FOR_SALE", "REJECTED", etc.; android: "NOT_AVAILABLE", "DRAFT", "IN_PROGRESS",
            "HALTED", "COMPLETED").
        sort: Optional sort field code. Allowed values: 1=Profile Name, 2=Create Date.
        sort_direction: Optional sort direction code. Allowed values: 1=ASC, 2=DESC.

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (list of publish profile objects), meta (page, page_size,
          platform_type, flow_status, market_place_type, has_rc_binary, store_status, sort,
          sort_direction, pagination metadata).
        - Error: success (false), error (tool, type, message, details).

    Examples:
        Get first page of iOS profiles: get_publish_profiles(platform_type="ios")
        Get page 2 with 10 items: get_publish_profiles(platform_type="android", page=2, size=10)
        Filter by flow status: get_publish_profiles(platform_type="ios", flow_status=0)
        Filter by marketplace and store status: get_publish_profiles(platform_type="ios", market_place_type=[1], store_status=["IN_REVIEW"])
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

        allowed_market_place_types = MARKET_PLACE_TYPES[platform_type]
        if market_place_type is not None:
            invalid = [v for v in market_place_type if v not in allowed_market_place_types]
            if invalid:
                return error_response(
                    tool=TOOL_NAME,
                    type="validation_error",
                    message=(
                        f"Invalid market_place_type: {invalid}. Allowed values for platform_type="
                        f"'{platform_type}': {sorted(allowed_market_place_types)}"
                    ),
                )

        allowed_store_statuses = STORE_STATUSES[platform_type]
        if store_status is not None:
            invalid = [v for v in store_status if v not in allowed_store_statuses]
            if invalid:
                return error_response(
                    tool=TOOL_NAME,
                    type="validation_error",
                    message=(
                        f"Invalid store_status: {invalid}. Allowed values for platform_type="
                        f"'{platform_type}': {sorted(allowed_store_statuses)}"
                    ),
                )

        if sort is not None and sort not in SORT_FIELDS:
            return error_response(
                tool=TOOL_NAME,
                type="validation_error",
                message=f"Invalid sort: {sort}. Allowed values: {sorted(SORT_FIELDS)}",
            )
        if sort_direction is not None and sort_direction not in SORT_DIRECTIONS:
            return error_response(
                tool=TOOL_NAME,
                type="validation_error",
                message=f"Invalid sort_direction: {sort_direction}. Allowed values: {sorted(SORT_DIRECTIONS)}",
            )

        params: Dict[str, Any] = {
            "page": str(page),
            "size": str(size),
        }
        if flow_status is not None:
            params["flowStatus"] = str(flow_status)
        if market_place_type is not None:
            params["marketPlaceType"] = market_place_type
        if has_rc_binary is not None:
            params["hasRcBinary"] = str(has_rc_binary).lower()
        if store_status is not None:
            params["storeStatus"] = store_status
        if sort is not None:
            params["sort"] = sort
        if sort_direction is not None:
            params["sortDirection"] = sort_direction

        logger.debug(
            f"Fetching publish profiles - platform_type: {platform_type}, page: {page}, size: {size}, "
            f"flow_status: {flow_status}, market_place_type: {market_place_type}, "
            f"has_rc_binary: {has_rc_binary}, store_status: {store_status}, sort: {sort}, "
            f"sort_direction: {sort_direction}"
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
        meta = _build_meta_from_pagination(
            pagination,
            page,
            size,
            platform_type,
            flow_status,
            market_place_type,
            has_rc_binary,
            store_status,
            sort,
            sort_direction,
        )
        meta["count"] = count

        logger.info(
            f"Successfully retrieved {count} publish profiles for '{platform_type}' (page {page})"
        )

        return success_response(data=data, meta=meta)

    except Exception as e:
        logger.error(f"Failed to get publish profiles: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
