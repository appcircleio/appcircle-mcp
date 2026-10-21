"""Update app version release notes tool (write/action)."""

from typing import Any, Dict

from mcp.types import ToolAnnotations

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.validation import path_segment
from ...core.error_handler import handle_write_api_error
from ...core.logger import logger
from ...schemas.responses import success_response

TOOL_NAME = "update_app_version_release_notes"

# Key to exclude from the returned app version (security)
EXCLUDED_KEY = "certThumbPrints"


def _trim_app_version(app_version: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of the app version without certThumbPrints."""
    out = dict(app_version)
    out.pop(EXCLUDED_KEY, None)
    return out


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
    )
)
async def update_app_version_release_notes(
    profile_id: str,
    app_version_id: str,
    message: str,
) -> Dict[str, Any]:
    """
    SIDE EFFECT: Overwrites the release notes ("message") shown to testers for a
    distribution app version. This is a write tool -- it replaces the existing
    release notes text.

    Args:
        profile_id: The distribution profile ID (e.g. UUID).
        app_version_id: The app version ID (e.g. UUID).
        message: The new release notes text.

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (the updated app version object, excluding
          certThumbPrints), meta (empty).
        - Error: success (false), error (tool, type, message, details). type is invalid_state
          (HTTP 409/422) when the app version is not in a state that allows this update.

    Examples:
        Update release notes: update_app_version_release_notes(profile_id="p-uuid", app_version_id="v-uuid", message="Bug fixes and improvements")
    """
    try:
        logger.debug(
            f"Updating app version release notes - profile_id: {profile_id}, "
            f"app_version_id: {app_version_id}"
        )

        api_client = ApiClient()
        response = await api_client.patch(
            f"/distribution/v3/profiles/{path_segment(profile_id, 'profile_id')}/app-versions/{path_segment(app_version_id, 'app_version_id')}/message",
            json_data={"message": message},
        )

        response = _trim_app_version(response) if isinstance(response, dict) else {}

        logger.info(
            f"Successfully updated release notes for app version {app_version_id}"
        )

        return success_response(data=response, meta={})

    except Exception as e:
        logger.error(f"Failed to update app version release notes: {str(e)}")
        return handle_write_api_error(e, TOOL_NAME)
