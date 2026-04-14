"""Get bundle identifiers tool."""

from typing import Any, Dict, List

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...schemas.responses import success_response

TOOL_NAME = "get_bundle_identifiers"

ENDPOINT = "/signing-identity/v2/bundle-identifier"


def _normalize_bundle_identifiers_response(response: Any) -> List[Dict[str, Any]]:
    """Return list of bundle identifiers from API response (list or wrapper)."""
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        return response.get("data") or response.get("items") or response.get("bundleIdentifiers") or []
    return []


@mcp.tool()
async def get_bundle_identifiers() -> Dict[str, Any]:
    """
    Get all bundle identifiers for the organization.

    Returns the list of bundle identifiers (iOS/macOS app bundle IDs) registered
    in Appcircle, including id, name, identifier, platform, capabilities, and related metadata.

    Takes no parameters.

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (list of bundle identifier objects), meta (count).
        - Error: success (false), error (tool, type, message, details).

    Examples:
        Get all bundle identifiers: get_bundle_identifiers()
    """
    try:
        logger.debug("Fetching bundle identifiers")

        api_client = ApiClient()
        response = await api_client.get(ENDPOINT)

        items = _normalize_bundle_identifiers_response(response)
        count = len(items)

        logger.info(f"Successfully retrieved {count} bundle identifiers")

        return success_response(data=items, meta={"count": count})

    except Exception as e:
        logger.error(f"Failed to get bundle identifiers: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
