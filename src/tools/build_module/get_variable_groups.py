"""Get variable groups tool."""

from typing import Any, Dict, List

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...schemas.responses import success_response

TOOL_NAME = "get_variable_groups"

ENDPOINT = "/build/v2/variable-groups"


def _normalize_variable_groups_response(response: Any) -> List[Dict[str, Any]]:
    """Return list of variable groups from API response (list or wrapper)."""
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        data = response.get("data") or response.get("items") or response.get("variableGroups") or []
        return data if isinstance(data, list) else []
    return []


@mcp.tool()
async def get_variable_groups() -> Dict[str, Any]:
    """
    Get all build environment variable groups for the organization.

    Returns each variable group's ID, name, sub-organization sharing settings,
    and its variables (key, value, isSecret, isFile). Secret variable values
    are already redacted by the API (empty string when isSecret is true).

    Takes no parameters.

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (list of variable group objects), meta (count).
        - Error: success (false), error (tool, type, message, details).

    Examples:
        Get all variable groups: get_variable_groups()
    """
    try:
        logger.debug("Fetching variable groups")

        api_client = ApiClient()
        response = await api_client.get(ENDPOINT)

        data = _normalize_variable_groups_response(response)
        count = len(data)

        logger.info(f"Successfully retrieved {count} variable groups")

        return success_response(data=data, meta={"count": count})

    except Exception as e:
        logger.error(f"Failed to get variable groups: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
