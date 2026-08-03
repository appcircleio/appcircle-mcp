"""Get testing groups tool."""

from typing import Any, Dict, List

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...schemas.responses import success_response

TOOL_NAME = "get_testing_groups"

ENDPOINT = "/distribution/v2/testing-groups"


def _normalize_testing_groups_response(response: Any) -> List[Dict[str, Any]]:
    """Return list of testing groups from API response (list or wrapper)."""
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        data = response.get("data") or response.get("items") or response.get("testingGroups") or []
        return data if isinstance(data, list) else []
    return []


@mcp.tool()
async def get_testing_groups() -> Dict[str, Any]:
    """
    Get all testing distribution groups for the organization.

    Returns each testing group's ID, name, member tester emails, group type,
    and (for externally-synced groups) external group name.

    Takes no parameters.

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (list of testing group objects), meta (count).
        - Error: success (false), error (tool, type, message, details).

    Examples:
        Get all testing groups: get_testing_groups()
    """
    try:
        logger.debug("Fetching testing groups")

        api_client = ApiClient()
        response = await api_client.get(ENDPOINT)

        data = _normalize_testing_groups_response(response)
        count = len(data)

        logger.info(f"Successfully retrieved {count} testing groups")

        return success_response(data=data, meta={"count": count})

    except Exception as e:
        logger.error(f"Failed to get testing groups: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
