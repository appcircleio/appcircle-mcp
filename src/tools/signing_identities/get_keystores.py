"""Get keystores tool."""

from typing import Any, Dict, List

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...schemas.responses import success_response

TOOL_NAME = "get_keystores"

ENDPOINT = "/signing-identity/v2/keystores"

# Keys to exclude from keystore response (sensitive / not needed for tool contract)
EXCLUDED_KEYSTORE_KEYS = (
    "password",
    "aliasPassword",
    "binary",
    "checkSum",
    "sha256FingerPrint",
)


def _normalize_keystores_response(response: Any) -> List[Dict[str, Any]]:
    """Return list of keystores from API response (list or wrapper)."""
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        return response.get("data") or response.get("items") or response.get("keystores") or []
    return []


def _trim_keystore(keystore: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of the keystore without excluded keys."""
    out = dict(keystore)
    for key in EXCLUDED_KEYSTORE_KEYS:
        out.pop(key, None)
    return out


@mcp.tool()
async def get_keystores() -> Dict[str, Any]:
    """
    Get all keystores for the organization.

    Returns the list of keystores (e.g. Android signing keystores) registered
    in Appcircle. Sensitive fields (password, aliasPassword, binary, checkSum,
    sha256FingerPrint) are omitted from the response.

    Takes no parameters.

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (list of keystore objects), meta (count).
        - Error: success (false), error (tool, type, message, details).

    Examples:
        Get all keystores: get_keystores()
    """
    try:
        logger.debug("Fetching keystores")

        api_client = ApiClient()
        response = await api_client.get(ENDPOINT)

        items_raw = _normalize_keystores_response(response)
        items = [_trim_keystore(k) for k in items_raw]
        count = len(items)

        logger.info(f"Successfully retrieved {count} keystores")

        return success_response(data=items, meta={"count": count})

    except Exception as e:
        logger.error(f"Failed to get keystores: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
