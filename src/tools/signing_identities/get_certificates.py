"""Get certificates tool."""

from typing import Any, Dict, List

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...schemas.responses import success_response

TOOL_NAME = "get_certificates"

ENDPOINT = "/signing-identity/v2/certificates"

# Keys to exclude from certificate response (sensitive / not needed for tool contract)
EXCLUDED_CERTIFICATE_KEYS = ("p12Password", "p12Binary", "metaData", "thumbprint")


def _normalize_certificates_response(response: Any) -> List[Dict[str, Any]]:
    """Return list of certificates from API response (list or wrapper)."""
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        return response.get("data") or response.get("items") or response.get("certificates") or []
    return []


def _trim_certificate(cert: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of the certificate without excluded keys."""
    out = dict(cert)
    for key in EXCLUDED_CERTIFICATE_KEYS:
        out.pop(key, None)
    return out


@mcp.tool()
async def get_certificates() -> Dict[str, Any]:
    """
    Get all signing certificates for the organization.

    Returns the list of signing certificates (e.g. distribution/development)
    registered in Appcircle. Sensitive fields (p12Password, p12Binary, metaData,
    thumbprint) are omitted from the response.

    Takes no parameters.

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (list of certificate objects), meta (count).
        - Error: success (false), error (tool, type, message, details).

    Examples:
        Get all certificates: get_certificates()
    """
    try:
        logger.debug("Fetching certificates")

        api_client = ApiClient()
        response = await api_client.get(ENDPOINT)

        items_raw = _normalize_certificates_response(response)
        items = [_trim_certificate(c) for c in items_raw]
        count = len(items)

        logger.info(f"Successfully retrieved {count} certificates")

        return success_response(data=items, meta={"count": count})

    except Exception as e:
        logger.error(f"Failed to get certificates: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
