"""Get commits by branch tool."""

from typing import Dict, Any, Optional, List, Tuple

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...schemas.responses import success_response

TOOL_NAME = "get_commits_by_branch"


def _build_meta_from_pagination(
    pagination: Optional[Dict[str, Any]], page: int, size: int
) -> Dict[str, Any]:
    """Build meta dict from API pagination object (commits pagination)."""
    base = {"page": page, "page_size": size}
    if not isinstance(pagination, dict):
        return base
    base["page"] = pagination.get("page", page)
    base["page_size"] = pagination.get("perPage", size)
    base["page_count"] = pagination.get("pageCount")
    base["total_count"] = pagination.get("totalCount")
    base["enable_previous"] = pagination.get("enablePrevious")
    base["enable_next"] = pagination.get("enableNext")
    return base


def _normalize_commits_response(response: Any) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Return (commits list, pagination dict or None) from API response."""
    if isinstance(response, list):
        return response, None
    if isinstance(response, dict):
        data = response.get("data") or response.get("commits") or []
        if not isinstance(data, list):
            data = []
        pagination = response.get("pagination")
        return data, pagination if isinstance(pagination, dict) else None
    return [], None


@mcp.tool()
async def get_commits_by_branch(
    branch_id: str,
    page: Optional[int] = None,
    size: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Get commits for a build branch (paginated).

    Returns a list of commits for the given branch ID, including commit hash,
    message, author, commit date, tags, and associated builds. When page and
    size are provided, the API returns pagination metadata (page, perPage,
    pageCount, totalCount, enablePrevious, enableNext) which is included in meta.

    Args:
        branch_id: The branch ID (e.g. UUID).
        page: Page number (1-based). If provided with size, enables pagination and
            returns pagination metadata in meta. Default when using pagination: 1.
        size: Page size. If provided with page, enables pagination. Default when
            using pagination: 25. Values above 100 are capped at 100.

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (list of commit objects with id, hash,
          message, author, email, commitDate, tags, builds, etc.), meta (when
          pagination used: page, page_size, page_count, total_count,
          enable_previous, enable_next; otherwise empty or minimal).
        - Error: success (false), error (tool, type, message, details).

    Examples:
        Get commits (no pagination): get_commits_by_branch(branch_id="branch-uuid")
        Get first page of commits: get_commits_by_branch(branch_id="branch-uuid", page=1, size=25)
        Get page 2 with 10 items: get_commits_by_branch(branch_id="branch-uuid", page=2, size=10)
    """
    try:
        params: Dict[str, str] = {"branchId": branch_id}
        use_pagination = page is not None or size is not None

        if use_pagination:
            page_val = 1 if page is None or page < 1 else page
            size_val = 25 if size is None else size
            if size_val > 100:
                logger.warning(f"Requested size {size_val} exceeds maximum 100, using 100")
                size_val = 100
            if size_val < 1:
                size_val = 1
            params["page"] = str(page_val)
            params["size"] = str(size_val)
        else:
            page_val = 1
            size_val = 25

        logger.debug(
            f"Fetching commits by branch - branch_id: {branch_id}, "
            + (f"page: {page_val}, size: {size_val}" if use_pagination else "no pagination")
        )

        api_client = ApiClient()
        response = await api_client.get("/build/v2/commits", params=params)

        commits, pagination = _normalize_commits_response(response)
        count = len(commits)

        if use_pagination:
            meta = _build_meta_from_pagination(pagination, page_val, size_val)
        else:
            meta = {"count": count}

        logger.info(
            f"Successfully retrieved {count} commits for branch {branch_id}"
            + (f" (page {page_val})" if use_pagination else "")
        )

        return success_response(data=commits, meta=meta)

    except Exception as e:
        logger.error(f"Failed to get commits by branch: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
