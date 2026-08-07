"""Get last commit tool."""

from typing import Dict, Any

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...schemas.responses import success_response

TOOL_NAME = "get_last_commit"


@mcp.tool()
async def get_last_commit(branch_id: str) -> Dict[str, Any]:
    """
    Get the most recent commit on a build branch.

    Returns the latest commit for the given branch ID, including commit hash,
    message, author, commit date, and tags.

    Args:
        branch_id: The branch ID (e.g. UUID).

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (commit object with id, organizationId,
          profileId, branchId, hash, message, author, eMail, commitDate, tags,
          targetBranchId, targetHash, pullNumber), meta (empty).
        - Error: success (false), error (tool, type, message, details).

    Examples:
        Get the last commit on a branch: get_last_commit(branch_id="branch-uuid")
    """
    try:
        logger.debug(f"Fetching last commit - branch_id: {branch_id}")

        api_client = ApiClient()
        response = await api_client.get(
            "/build/v2/commits/last-commit", params={"branchId": branch_id}
        )

        if isinstance(response, dict):
            data = response.get("data") or response.get("commit") or response
        else:
            data = {}

        if not isinstance(data, dict):
            data = {}

        logger.info(f"Successfully retrieved last commit for branch {branch_id}")

        return success_response(data=data, meta={})

    except Exception as e:
        logger.error(f"Failed to get last commit: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
