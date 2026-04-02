"""Get commit details tool."""

from typing import Dict, Any, Optional

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...schemas.responses import success_response, error_response

TOOL_NAME = "get_commit_details"


@mcp.tool()
async def get_commit_details(
    commit_id: Optional[str] = None,
    commit_hash: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get a single commit by commit ID (UUID) or by commit hash (git SHA).

    Returns the commit with the given identifier, including hash, message,
    author, email, commit date, tags, and associated builds (with status,
    failed step, duration, artifacts, etc.). Provide either commit_id or
    commit_hash, not both.

    Args:
        commit_id: The commit ID (UUID). Use when you have the commit's unique ID.
        commit_hash: The commit hash (git SHA, e.g. 40-char hex). Use when you have
            the repository commit hash.

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (commit object with id, organizationId,
          profileId, branchId, hash, message, author, email, commitDate, tags,
          builds, targetBranchId, pullNumber, commitStatus, description, etc.), meta (empty).
        - Error: success (false), error (tool, type, message, details).

    Examples:
        Get by commit ID: get_commit_details(commit_id="f4e4d8f9-ae28-4e82-a7bd-5e02338c2260")
        Get by commit hash: get_commit_details(commit_hash="15d2bb0bac20cd8a564d4dbdf7bf2948321f7908")
    """
    has_id = bool(commit_id and str(commit_id).strip())
    has_hash = bool(commit_hash and str(commit_hash).strip())
    if has_id and has_hash:
        return error_response(
            tool=TOOL_NAME,
            type="validation_error",
            message="Provide either commit_id or commit_hash, not both.",
            details={"commit_id": commit_id, "commit_hash": commit_hash},
        )
    if not has_id and not has_hash:
        return error_response(
            tool=TOOL_NAME,
            type="validation_error",
            message="Provide either commit_id or commit_hash.",
            details=None,
        )

    identifier = (commit_id or commit_hash).strip()
    by_id = has_id

    try:
        logger.debug(
            f"Fetching commit details - {'commit_id' if by_id else 'commit_hash'}: {identifier}"
        )

        api_client = ApiClient()
        response = await api_client.get(f"/build/v2/commits/{identifier}")

        if isinstance(response, dict):
            data = response.get("data") or response.get("commit") or response
        else:
            data = {}

        if not isinstance(data, dict):
            data = {}

        logger.info(
            f"Successfully retrieved commit details for {'commit_id' if by_id else 'commit_hash'} {identifier}"
        )

        return success_response(data=data, meta={})

    except Exception as e:
        logger.error(f"Failed to get commit details: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
