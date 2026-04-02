"""
Standard response envelope for all MCP tools.

Every tool returns either:
- Success: { "success": true, "data": <tool-specific>, "meta": { ... } }
- Error:   { "success": false, "error": { "tool", "type", "message", "details" } }

Use success_response() for success; use handle_api_error() from core.error_handler
for errors (core maps exceptions to this shape via error_response()).
"""

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class ToolErrorDetail(BaseModel):
    """Standard error payload returned inside the error envelope."""

    tool: str = Field(..., description="Name of the tool that raised the error")
    type: str = Field(
        ...,
        description="Error kind: http_error, request_error, timeout_error, validation_error, unknown_error",
    )
    message: str = Field(..., description="Human-readable error message")
    details: Any = Field(default=None, description="Extra details (e.g. API message, exception string)")
    status_code: Optional[int] = Field(
        default=None,
        description="HTTP status code (present only for type=http_error)",
    )


class ToolErrorResponse(BaseModel):
    """Standard error response envelope."""

    success: Literal[False] = False
    error: ToolErrorDetail


class ToolSuccessResponse(BaseModel):
    """Standard success response envelope."""

    success: Literal[True] = True
    data: Any = Field(..., description="Tool-specific payload (list, dict, etc.)")
    meta: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata: count, page, page_size, filters, etc.",
    )


def success_response(
    data: Any,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a standard success response dict for tools.

    Args:
        data: Tool-specific payload (e.g. list of profiles, report rows).
        meta: Optional metadata (e.g. count, page, page_size, filters).
              Omitted keys are not included; pass {} or None for no meta.

    Returns:
        Dict with keys: success (True), data, meta (defaults to {}).

    Example:
        return success_response(
            data=profiles,
            meta={"count": len(profiles), "search_term": search},
        )
    """
    return {
        "success": True,
        "data": data,
        "meta": meta if meta is not None else {},
    }


def error_response(
    tool: str,
    type: str,
    message: str,
    details: Any = None,
    status_code: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Build a standard error response dict (same shape as handle_api_error output).

    Core uses this to build error responses from exceptions. Tools should call
    handle_api_error(exception, tool_name) from core.error_handler; use this
    only when returning an error from non-exception context.
    """
    error: Dict[str, Any] = {
        "tool": tool,
        "type": type,
        "message": message,
        "details": details,
    }
    if status_code is not None:
        error["status_code"] = status_code
    return {"success": False, "error": error}
