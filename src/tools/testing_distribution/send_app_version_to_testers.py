"""Send app version to testers tool (write/action)."""

from typing import Any, Dict, List

from mcp.types import ToolAnnotations

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.validation import path_segment
from ...core.error_handler import handle_write_api_error
from ...core.logger import logger
from ...schemas.responses import success_response

TOOL_NAME = "send_app_version_to_testers"


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
    )
)
async def send_app_version_to_testers(
    profile_id: str,
    app_version_id: str,
    message: str,
    testers: List[str],
) -> Dict[str, Any]:
    """
    SIDE EFFECT: Sends a distribution app version to testers, notifying them
    with the given message. This is a write/action tool -- it dispatches a real
    notification/distribution task, it does not just read data.

    Args:
        profile_id: The distribution profile ID (e.g. UUID).
        app_version_id: The app version ID (e.g. UUID).
        message: The notification message shown to testers.
        testers: List of testers to send to. Each entry is either a tester's
            email address or a testing group ID (the "id" field from
            get_testing_groups).

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data ({"taskId": <uuid>}), meta (profile_id, app_version_id, testers).
        - Error: success (false), error (tool, type, message, details). type is invalid_state
          (HTTP 409/422) when the app version is not in a state that allows this action.

    Examples:
        Send to individual testers: send_app_version_to_testers(profile_id="p-uuid", app_version_id="v-uuid", message="New build ready", testers=["tester@example.com"])
        Send to a testing group: send_app_version_to_testers(profile_id="p-uuid", app_version_id="v-uuid", message="New build ready", testers=["group-uuid"])
    """
    try:
        logger.debug(
            f"Sending app version to testers - profile_id: {profile_id}, "
            f"app_version_id: {app_version_id}, tester_count: {len(testers) if testers else 0}"
        )

        api_client = ApiClient()
        response = await api_client.post(
            f"/distribution/v2/profiles/{path_segment(profile_id, 'profile_id')}/app-versions/{path_segment(app_version_id, 'app_version_id')}",
            json_data={"message": message, "testers": testers},
            params={"action": "sendToTesting"},
        )

        data = response if isinstance(response, dict) else {}

        logger.info(f"Successfully sent app version {app_version_id} to testers: {data}")

        meta = {
            "profile_id": profile_id,
            "app_version_id": app_version_id,
            "testers": testers,
        }
        return success_response(data=data, meta=meta)

    except Exception as e:
        logger.error(f"Failed to send app version to testers: {str(e)}")
        return handle_write_api_error(e, TOOL_NAME)
