# Tool response envelope

All tools return a **standard envelope** so every MCP client can parse results the same way. Request/response format and error handling are described below.

## Success 

```json
{
  "success": true,
  "data": <tool-specific payload>,
  "meta": { ... }
}
```

| Field     | Type   | Description |
|-----------|--------|-------------|
| `success` | `true` | Always `true` for success. |
| `data`    | any    | Tool-specific payload (list, object, etc.). |
| `meta`    | object | Optional metadata; may be `{}`. Common keys: `count`, `page`, `page_size`, `total_count`, `total_pages`, `has_more`, `filters`, `search_term`. |

**Example (get_build_profiles):**

```json
{
  "success": true,
  "data": [
    { "id": "uuid-1", "name": "iOS Production", "buildPlatformType": 1 }
  ],
  "meta": {
    "count": 1,
    "search_term": "iOS"
  }
}
```

## Error

```json
{
  "success": false,
  "error": {
    "tool": "<tool_name>",
    "type": "<error_type>",
    "message": "<human-readable message>",
    "details": "<extra details>",
    "status_code": 401
  }
}
```

| Field            | Type   | Description |
|------------------|--------|-------------|
| `success`        | `false`| Always `false` for errors. |
| `error`          | object| Error details. |
| `error.tool`     | string| Name of the tool that failed. |
| `error.type`     | string| One of: `http_error`, `request_error`, `timeout_error`, `validation_error`, `unknown_error`. |
| `error.message`  | string| Short, human-readable message. |
| `error.details`  | any   | API message, exception string, or other details. |
| `error.status_code` | number | Present only for `type: "http_error"` (e.g. 401, 404, 500). |

**Example:**

```json
{
  "success": false,
  "error": {
    "tool": "get_build_profiles",
    "type": "http_error",
    "message": "Unauthorized - Invalid or expired access token",
    "details": "Invalid token",
    "status_code": 401
  }
}
```

## Implementation (for server developers)

- **Success:** Use `success_response(data=..., meta=...)` from `src.schemas.responses`.
- **Error:** Use `handle_api_error(exception, tool_name)` from `src.core.error_handler`. Core maps exceptions (httpx, etc.) to the envelope by calling `error_response(...)` from schemas, so the shape is defined in one place (`src.schemas.responses`).
