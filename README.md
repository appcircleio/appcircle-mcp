# Appcircle MCP Server

MCP server for [Appcircle](https://appcircle.io): exposes Build, Signing Identities, Testing Distribution, Enterprise App Store, Publish to Stores, and Reporting tools to any MCP-capable client (Claude Desktop, Cursor, VS Code, etc.). The Appcircle MCP Server acts as the bridge between AI tools and Appcircle; thus, AI agents, assistants and chatbots to safely access and interact with Appcircle resources through structured, governed, and task-level tools.

## Use Cases

- CI/CD and Workflow Intelligence: Monitor pipeline runs, track release status, and get insights into your mobile CI/CD workflows.
- Configuration and Environment Insights: Query build configurations and signing setup to understand how a project is configured and where issues may originate.
- Reporting and Operational Insights: Generate summaries of CI stability, recurring issues, pipeline performance, and overall CI/CD health. 


## Running Modes

You can use the MCP server in four ways:

| Mode | Summary |
|------|--------|
| **1. Remote host** | Connect to **https://mcp.appcircle.io**. No local install; your client sends your Appcircle token (e.g. `Authorization: Bearer <token>`) on each request. |
| **2. Local (stdio)** | Run the server from source: clone the repo, optionally use a venv, then run `appcircle-mcp` (default transport is stdio). Requires Python and pip. Set `APPCIRCLE_ACCESS_TOKEN` in the environment. Your MCP client runs the server as a subprocess. |
| **3. Local (streamable-http)** | Run the server locally over HTTP: use `--transport streamable-http` and optionally `--host` / `--port` (e.g. `appcircle-mcp --transport streamable-http --host 127.0.0.1 --port 8000`). Clients connect to that URL and send their token in the request. |
| **4. Local (Docker)** | Run the official Docker image on your machine. Requires Docker. Use the image’s default port or override with `--port`; see the image documentation for exact usage. |

Detailed client configuration (Cursor, Claude, etc.) lives in the dedicated [installation guides](docs/installation_guides/claude_applications.md); this section is a high-level summary only.

## Installation

Client-specific setup guides:

- **[Claude Applications](docs/installation_guides/claude_applications.md)** - Installation guide for Claude Desktop and Claude Code CLI.
- **[Cursor IDE](docs/installation_guides/cursor.md)** - Installation guide for Cursor IDE.
- **[Codex](docs/installation_guides/codex.md)** - Installation guide for Codex app and Codex CLI.
- **[Antigravity IDE](docs/installation_guides/antigravity.md)** - Installation guide for Antigravity IDE.
- **[VS Code (GitHub Copilot)](docs/installation_guides/vscode.md)** - Installation guide for VS Code with GitHub Copilot.
- **[Windsurf IDE](docs/installation_guides/windsurf.md)** - Installation guide for Windsurf IDE.
- **[Gemini CLI](docs/installation_guides/gemini_cli.md)** - Installation guide for Gemini CLI.
 - **[GitHub Copilot CLI](docs/installation_guides/copilot_cli.md)** - Installation guide for GitHub Copilot CLI.

## Configuration (Environment Variables)

| Variable | Required | Description |
|----------|----------|-------------|
| `APPCIRCLE_ACCESS_TOKEN` | Yes (stdio only) | Appcircle API access token. Required when using stdio transport. For streamable-http, each client sends its own token. See [Obtaining a token](docs/appcircle_access_token.md) for how to get one. |
| `APPCIRCLE_API_URL` | No | API base URL (default: `https://api.appcircle.io` may differ for self-hosted users). |
| `APPCIRCLE_MCP_ALLOWED_HOST` | No (streamable-http only) | Public hostname for the MCP server (e.g. `mcp.appcircle.io`). Set this when deploying behind a reverse proxy so the server accepts the `Host` header from clients. Omit for localhost. |
| `APPCIRCLE_MCP_PORT` | No (streamable-http only) | Bind port for the HTTP server (default: `8000`). Overridden by `--port` if provided. Useful for on-prem or Docker when a specific port is required. |
| `LOG_LEVEL` | No | Logging level, e.g. `DEBUG`, `INFO` (default: `INFO`). |
| `APPCIRCLE_EXCLUDED_TOOLSETS` | No | Comma-separated toolsets to exclude (e.g. `build_module,report`). See [Toolsets](#toolsets) below. |

Set these in your shell or in your MCP client’s configuration.

## Toolsets

### Available Toolsets

The following sets of tools are available:

| Toolset | Description |
|---------|-------------|
| `build_module` | Build profiles, configurations, workflows, commits, and pipeline operations |
| `signing_identities` | Signing identities and bundle identifiers |
| `testing_distribution` | Testing distribution profiles and distribution details |
| `publish_to_stores` | Publish profiles and store publishing operations |
| `enterprise_app_store` | Enterprise app store profiles and store details |
| `report` | Reporting: build history, distribution, signing, publish status, and related reports |

You can exclude one or more toolsets so their tools are not registered. Exclusions can be set via CLI arguments or the `APPCIRCLE_EXCLUDED_TOOLSETS` environment variable; both are merged (union).

- **CLI:** `--exclude toolset1 toolset2` or `--exclude-toolsets toolset1,toolset2`
- **Env:** `APPCIRCLE_EXCLUDED_TOOLSETS=build_module,report`

Example MCP config (Cursor / Claude Desktop) with exclusions:

```json
{
  "mcpServers": {
    "appcircle": {
      "command": "appcircle-mcp",
      "args": ["--exclude", "report"]
    }
  }
}
```

### Tools

Tools are exposed via MCP `tools/list`. Reference below lists all tools by toolset; for response shape and examples see [docs/tool_contract.md](docs/tool_contract.md).

<!-- START AUTOMATED TOOLS -->
<details>

<summary>Build</summary>

- **get_build_profiles** - Get build profiles for the current organization (paginated). Optionally filter by profile name.
  - **Access level:** read
  - `page`: Page number (1-based). Default: 1. (number, optional)
  - `size`: Page size (1-100). Default: 25. Values above 100 are capped at 100. (number, optional)
  - `search`: Optional search term to filter profiles by name (case-insensitive partial match). (string, optional)

- **get_build_profile_details** - Get a single build profile by ID, optionally including its build configurations.
  - **Access level:** read
  - `profile_id`: The build profile ID (e.g. UUID). (string, required)
  - `configurations`: If true, also fetch the profile's build configurations. Default: false. (boolean, optional)

- **get_build_configuration_details** - Get a single build configuration by profile ID and configuration ID.
  - **Access level:** read
  - `profile_id`: The build profile ID (e.g. UUID). (string, required)
  - `configuration_id`: The build configuration ID (e.g. UUID). (string, required)

- **get_build_profile_workflows** - Get workflows for a build profile by profile ID.
  - **Access level:** read
  - `profile_id`: The build profile ID (e.g. UUID). (string, required)

- **get_workflow_detail** - Get a single workflow by build profile ID and workflow ID.
  - **Access level:** read
  - `profile_id`: The build profile ID (e.g. UUID). (string, required)
  - `workflow_id`: The workflow ID (e.g. UUID). (string, required)

- **get_commits_by_branch** - Get commits for a build branch (paginated).
  - **Access level:** read
  - `branch_id`: The branch ID (e.g. UUID). (string, required)
  - `page`: Page number (1-based). If provided with size, enables pagination. Default: 1. (number, optional)
  - `size`: Page size. If provided with page, enables pagination. Default: 25, max 100. (number, optional)

- **get_commit_details** - Get a single commit by commit ID (UUID) or by commit hash (git SHA). Provide either commit_id or commit_hash, not both.
  - **Access level:** read
  - `commit_id`: The commit ID (UUID). (string, optional)
  - `commit_hash`: The commit hash (git SHA). (string, optional)

</details>

<details>

<summary>Signing Identities</summary>

- **get_bundle_identifiers** - Get all bundle identifiers for the organization (iOS/macOS app bundle IDs).
  - **Access level:** read
  - No parameters.

- **get_certificates** - Get all signing certificates for the organization. Sensitive fields (p12Password, p12Binary, metaData, thumbprint) are omitted.
  - **Access level:** read
  - No parameters.

- **get_keystores** - Get all keystores for the organization (e.g. Android signing keystores). Sensitive fields (password, aliasPassword, binary, checkSum, sha256FingerPrint) are omitted.
  - **Access level:** read
  - No parameters.

- **get_provisioning_profiles** - Get provisioning profiles for the organization (e.g. iOS/macOS). Sensitive/large fields (binary, metaData, certificateThumbPrints, provisionedDevices, connectApiKeyId) are omitted. Optionally filter by app (bundle) ID.
  - **Access level:** read
  - `app_id`: Optional app (bundle) ID to filter provisioning profiles (e.g. com.example.app). (string, optional)

</details>

<details>

<summary>Testing Distribution</summary>

- **get_distribution_profiles** - Get testing distribution profiles for the current organization (paginated). Optionally filter by profile name.
  - **Access level:** read
  - `page`: Page number (1-based). Default: 1. (number, optional)
  - `size`: Page size (1-100). Default: 25, max 100. (number, optional)
  - `search`: Optional search term to filter profiles by name. (string, optional)

- **get_distribution_profile_details** - Get a single testing distribution profile by ID (with optional app versions pagination).
  - **Access level:** read
  - `profile_id`: The distribution profile ID (e.g. UUID). (string, required)
  - `page`: Page number for app versions (1-based). Default: 1. (number, optional)
  - `size`: Page size for app versions (1-100). Default: 25, max 100. (number, optional)

</details>

<details>

<summary>Publish to Stores</summary>

- **get_publish_profiles** - Get publish profiles for the current organization for a given platform type (paginated). Optionally filter by flow status.
  - **Access level:** read
  - `platform_type`: Platform type of publish profiles ("ios" or "android"). (string, required)
  - `page`: Page number (1-based). Default: 1. (number, optional)
  - `size`: Page size (1-100). Default: 25, max 100. (number, optional)
  - `flow_status`: Optional flow status code to filter by (e.g. 0=Success, 1=Failed, 91=Running). (number, optional)

- **get_publish_profile_details** - Get a single publish profile by platform type and ID (with optional app versions pagination).
  - **Access level:** read
  - `platform_type`: Platform type ("ios" or "android"). (string, required)
  - `profile_id`: The publish profile ID (e.g. UUID). (string, required)
  - `page`: Page number for app versions (1-based). Default: 1. (number, optional)
  - `size`: Page size for app versions (1-100). Default: 25, max 100. (number, optional)

</details>

<details>

<summary>Enterprise App Store</summary>

- **get_store_profiles** - Get enterprise app store profiles for the current organization (paginated).
  - **Access level:** read
  - `page`: Page number (1-based). Default: 1. (number, optional)
  - `size`: Page size (1-100). Default: 25, max 100. (number, optional)

- **get_store_profile_details** - Get a single enterprise app store profile by ID (with optional app versions pagination).
  - **Access level:** read
  - `profile_id`: The enterprise app store profile ID (e.g. UUID). (string, required)
  - `page`: Page number for app versions (1-based). Default: 1. (number, optional)
  - `size`: Page size for app versions (1-100). Default: 25, max 100. (number, optional)

</details>

<details>

<summary>Report</summary>

- **get_build_history_report** - Get build history report, optionally filtered by date range, build profile, and organization. Paginated.
  - **Access level:** read
  - `start_date`: Optional start date (YYYY-MM-DD). (string, optional)
  - `end_date`: Optional end date (YYYY-MM-DD). (string, optional)
  - `page`: Page number (default: 1). (number, optional)
  - `size`: Items per page (1-100, default: 50). (number, optional)
  - `build_profile_name`: Filter by build profile name. (string, optional)
  - `organization_id`: Filter by organization UUID. (string, optional)

- **get_build_insights_report** - Get a computed Build Insights Report (Health Snapshot + Trends, Root Cause, Artifact Health, Workflow Quality, Queue Time, and Maturity Assessment analysis) over build history, aggregated server-side. Unlike get_build_history_report, this fetches every page internally and returns small pre-aggregated results instead of raw records.
  - **Access level:** read
  - `start_date`: Optional start date (YYYY-MM-DD) for the current period. Default: last 30 days. (string, optional)
  - `end_date`: Optional end date (YYYY-MM-DD) for the current period. (string, optional)
  - `sections`: Optional list of sections to compute: `health_snapshot`, `root_cause`, `artifact_health`, `workflow_quality`, `queue_time`, `maturity_assessment`. Default: all six. (array of strings, optional)
  - `include_sub_orgs`: If true, keep cross-org build records in history-derived metrics instead of filtering to the token's own organization. Default: false. (boolean, optional)

- **get_distribution_app_version_report** - Get daily usage report for distributed app versions. Paginated; supports filters by profile, OS, organization.
  - **Access level:** read
  - `start_date`: Optional start date (YYYY-MM-DD). (string, optional)
  - `end_date`: Optional end date (YYYY-MM-DD). (string, optional)
  - `page`: Page number (default: 1). (number, optional)
  - `size`: Items per page (1-100, default: 50). (number, optional)
  - `profile_name`: Filter by distribution profile name. (string, optional)
  - `os`: Filter by OS ("ios" or "android"). (string, optional)
  - `organization_id`: Filter by organization UUID. (string, optional)

- **get_distribution_sent_report** - Get daily usage report for distributed app sharing. Paginated; supports filters by profile, OS, organization.
  - **Access level:** read
  - `start_date`: Optional start date (YYYY-MM-DD). (string, optional)
  - `end_date`: Optional end date (YYYY-MM-DD). (string, optional)
  - `page`: Page number (default: 1). (number, optional)
  - `size`: Items per page (1-100, default: 50). (number, optional)
  - `profile_name`: Filter by distribution profile name. (string, optional)
  - `os`: Filter by OS ("ios" or "android"). (string, optional)
  - `organization_id`: Filter by organization UUID. (string, optional)

- **get_enterprise_app_store_app_usage_report** - Get app usage report for enterprise app store. start_date and end_date are required. Paginated.
  - **Access level:** read
  - `start_date`: Start date (YYYY-MM-DD). (string, required)
  - `end_date`: End date (YYYY-MM-DD). (string, required)
  - `page`: Page number (default: 1). (number, optional)
  - `size`: Items per page (1-100, default: 50). (number, optional)
  - `organization_id`: Optional filter by organization UUID. (string, optional)

- **get_publish_resign_report** - Get publish resign report, optionally filtered by date range, app name, organization, and status. Paginated.
  - **Access level:** read
  - `start_date`: Optional start date (YYYY-MM-DD). (string, optional)
  - `end_date`: Optional end date (YYYY-MM-DD). (string, optional)
  - `page`: Page number (default: 1). (number, optional)
  - `size`: Items per page (1-100, default: 50). (number, optional)
  - `app_name`: Filter by app name. (string, optional)
  - `organization_id`: Filter by organization UUID. (string, optional)
  - `status`: Filter by resign status (0=waiting, 1=processing, 2=succeeded, 3=failed, 4=cancelled, 5=timeout). (number, optional)

- **get_publish_status_report** - Get publish status report, optionally filtered by date range, app name, organization, and status. Paginated.
  - **Access level:** read
  - `start_date`: Optional start date (YYYY-MM-DD). (string, optional)
  - `end_date`: Optional end date (YYYY-MM-DD). (string, optional)
  - `page`: Page number (default: 1). (number, optional)
  - `size`: Items per page (1-100, default: 50). (number, optional)
  - `app_name`: Filter by app name. (string, optional)
  - `organization_id`: Filter by organization UUID. (string, optional)
  - `status`: Filter by publish status (e.g. 0=Success, 1=Failed, 91=Running). (number, optional)

- **get_signing_report** - Get signing report, optionally filtered by date range, organization, OS, and build status. Paginated.
  - **Access level:** read
  - `start_date`: Optional start date (YYYY-MM-DD). (string, optional)
  - `end_date`: Optional end date (YYYY-MM-DD). (string, optional)
  - `page`: Page number (default: 1). (number, optional)
  - `size`: Items per page (1-100, default: 50). (number, optional)
  - `organization_id`: Filter by organization UUID. (string, optional)
  - `os`: Filter by OS ("ios" or "android"). (string, optional)
  - `build_status`: Filter by build status (e.g. 0=Success, 1=Failed, 91=Running). (number, optional)

</details>
<!-- END AUTOMATED TOOLS -->

## Running the server

From the repo root:

```bash
python -m src.server
```

Or after `pip install -e .`:

```bash
appcircle-mcp
```

The server runs over stdio (or SSE/HTTP depending on how your client starts it).

## Response format

Every tool returns a **standard envelope**:

- **Success:** `{ "success": true, "data": <payload>, "meta": { ... } }`  
  `data` is the tool result; `meta` is optional (e.g. `count`, `page`, `filters`).
- **Error:** `{ "success": false, "error": { "tool", "type", "message", "details" } }`  
  Same shape for all tools so clients can parse errors consistently.

Full specification: [docs/tool_contract.md](docs/tool_contract.md).

## Testing

Install with dev dependencies:

```bash
pip install -e ".[dev]"
```

### Unit tests (default)

Use a mocked API; **no `APPCIRCLE_ACCESS_TOKEN`** needed. Default `pytest` only runs these (see `testpaths` in [pyproject.toml](pyproject.toml)):

```bash
pytest test/unit/ -v
```

- Single file: `pytest test/unit/tools/build_module/test_get_build_profiles.py -v`
- With coverage: `pytest test/unit/ --cov=src --cov-report=term-missing`

### Integration tests

Call the **real Appcircle API**. Set `APPCIRCLE_ACCESS_TOKEN` in the environment, then run:

```bash
pytest test/integration/ -v
```

- All integration tests: `pytest test/integration/ -v`
- By tool: `pytest test/integration/build_module/ -v`, `pytest test/integration/report/ -v`, etc.
- By marker: `pytest -m integration -v` (when running from repo root; includes only integration tests if both unit and integration are collected)

If `APPCIRCLE_ACCESS_TOKEN` is not set, integration tests are **skipped** (no failure).

**Optional env vars for integration tests** (when discovery fails or tests need real IDs; omit to skip those tests):

| Variable | Description |
|----------|-------------|
| `APPCIRCLE_TEST_ORGANIZATION_ID` | Organization UUID. Used by `test_with_organization_id` (enterprise app store app usage report). |
| `APPCIRCLE_TEST_BRANCH_ID` | Branch UUID. Used by get_commits_by_branch and related tests when no branch can be discovered from the API. |
| `APPCIRCLE_TEST_COMMIT_ID` | Commit UUID. Used by get_commit_details tests when no commit can be discovered from the API. |

## Security

This project depends on third-party open-source packages listed in
[pyproject.toml](pyproject.toml). While we pin dependency version ranges and
ship a lockfile (`uv.lock`) with cryptographic hashes, these packages are
maintained independently and provided "as-is." Appcircle makes no guarantees
regarding the security or reliability of third-party dependencies.

We recommend auditing installed packages before use:

```bash
uv run pip-audit
```
