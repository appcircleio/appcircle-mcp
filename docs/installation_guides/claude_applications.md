# Install Appcircle MCP Server in Claude Applications
## Claude Desktop

### Prerequisites

- **Claude Desktop** installed (latest version)
- **Appcircle access token** → see [Obtaining a token](../appcircle_access_token.md) for how to get one (Personal Access Key or API Keys)

### Open the config file

Open it from **Claude Desktop → Settings → Developer → Edit Config**.

After any config change, **fully restart Claude Desktop** (quit and reopen).

---

You can use the Appcircle MCP Server in four ways. Each section below provides an `mcpServers` entry for `claude_desktop_config.json`.

---

## 1. Remote server (mcp.appcircle.io)

No local install. Claude Desktop connects to Appcircle’s hosted MCP server and sends your token on each request.

Add this to your config (replace the token):

```json
{
  "mcpServers": {
    "appcircle": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://mcp.appcircle.io",
        "--header",
        "Authorization: Bearer appcircle_access_token"
      ]
    }
  }
}
```

---

## 2. Local (stdio)

Claude Desktop starts the server as a local subprocess (stdio).

### Prerequisites

- **Python 3.10+**
- **Appcircle access token** → see [Obtaining a token](../appcircle_access_token.md)

### Install the server

**From GitHub (clone and install):**

```bash
git clone https://github.com/appcircleio/appcircle-mcp.git
cd appcircle-mcp
pip install .
# or with uv:
uv pip install .
```

**Optional:** Use a virtual environment:

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install .
```

### Get the appcircle-mcp path

After installing, get the full path to the CLI

```bash
which appcircle-mcp
```

Example outputs:

- **venv:** `/path/to/appcircle-mcp/venv/bin/appcircle-mcp`
- **user install:** `~/.local/bin/appcircle-mcp`
- **pyenv:** `~/.pyenv/shims/appcircle-mcp` (or use `pyenv which appcircle-mcp` for the real binary)

Use this exact path in the next step.

### Claude Desktop setup

1. **Open the MCP config file** 
   - Claude Desktop → Settings → Developer → Edit Config

2. **Add the Appcircle server** (replace `PATH_FROM_WHICH_APPCIRCLE_MCP` with the path from the step above):

```json
{
  "mcpServers": {
    "appcircle": {
      "command": "PATH_FROM_WHICH_APPCIRCLE_MCP",
      "args": []
    }
  }
}
```

Example (venv in the repo):

```json
"appcircle": {
  "command": "/Users/you/appcircle-mcp/venv/bin/appcircle-mcp",
  "args": []
}
```

3. **Set your Appcircle token** (required for stdio):

   ```json
   "appcircle": {
     "command": "/path/to/appcircle-mcp",
     "args": [],
     "env": {
       "APPCIRCLE_ACCESS_TOKEN": "appcircle_access_token"
     }
   }
   ```

4. **Optional:** Exclude toolsets (e.g. skip report tools):

   ```json
   "args": ["--exclude", "report"]
   ```

5. **Restart Claude Desktop** and confirm the Appcircle tools appear.

---

## 3. Local (streamable-http)

You start the server yourself (HTTP), then Claude Desktop connects to it via `mcp-remote`.

**Security note:** When running locally, the server should bind only to localhost (`127.0.0.1`) rather than all network interfaces (`0.0.0.0`). The default `--host` is `127.0.0.1`.

### Prerequisites

- **Python 3.10+** (and the server installed as in Section 2, or run from repo)
- **Appcircle access token** → see [Obtaining a token](../appcircle_access_token.md)

### Install the server

Install as in **Section 2** (clone + `pip install .` from GitHub).

### Start the HTTP server

In a terminal, start the server and leave it running (replace `PATH_FROM_WHICH_APPCIRCLE_MCP` with the path from `which appcircle-mcp`):

```bash
PATH_FROM_WHICH_APPCIRCLE_MCP --transport streamable-http --host 127.0.0.1 --port 8000
```

Example (venv in the repo):

```bash
/Users/you/appcircle-mcp/venv/bin/appcircle-mcp --transport streamable-http --host 127.0.0.1 --port 8000
```

**Optional:** Exclude toolsets when starting the server (e.g. `--exclude report`). For the list of toolsets and exclusion options, see the [Toolsets](../../README.md#toolsets) section in the main README.

```bash
appcircle-mcp --transport streamable-http --host 127.0.0.1 --port 8000 --exclude report
```

### Claude Desktop setup

1. **Open the MCP config file** 
   - Claude Desktop → Settings → Developer → Edit Config

2. **Add the Appcircle server** (replace `appcircle_access_token` with your token):

```json
{
  "mcpServers": {
    "appcircle": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://localhost:8000",
        "--header",
        "Authorization: Bearer appcircle_access_token"
      ]
    }
  }
}
```

3. **Restart Claude Desktop** and confirm the Appcircle tools appear.

---

## 4. Local (Docker)

Run the server in a Docker container (HTTP), then Claude Desktop connects to it via `mcp-remote`.

### Prerequisites

- **Docker**
- **Appcircle access token** → see [Obtaining a token](../appcircle_access_token.md)

### Build and run the container

**From the repo (clone and build):**

```bash
git clone https://github.com/appcircleio/appcircle-mcp.git
cd appcircle-mcp
docker build -t appcircle-mcp-server .
docker run -d --name appcircle-mcp -p 8000:8000 appcircle-mcp-server
```
The server listens on `http://localhost:8000`. The client sends the token; no env vars are required in the container.

**Optional:** Exclude toolsets by passing env when running. For the list of toolsets, see the [Toolsets](../../README.md#toolsets) section in the main README.

```bash
docker run -d --name appcircle-mcp -p 8000:8000 -e APPCIRCLE_EXCLUDED_TOOLSETS=report appcircle-mcp-server
```

### Claude Desktop setup

1. **Open the MCP config file** 
   - Claude Desktop → Settings → Developer → Edit Config

2. **Add the Appcircle server** (replace `appcircle_access_token` with your token):

```json
{
  "mcpServers": {
    "appcircle": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://localhost:8000",
        "--header",
        "Authorization: Bearer appcircle_access_token"
      ]
    }
  }
}
```

3. **Restart Claude Desktop** and confirm the Appcircle tools appear.

---

## Troubleshooting

- **Server not showing in Claude:** Ensure the JSON is valid and you fully restarted Claude Desktop.
- **401 Unauthorized:** Your access token may have expired (tokens are valid about 24 hours). Generate a new one and update your config or auth. See [Obtaining a token](../appcircle_access_token.md) and the [Troubleshooting section](../appcircle_access_token.md#troubleshooting) there.
- **Streamable-http / Docker:** Confirm the server is running (`http://localhost:8000/health`) and that the client is sending `Authorization: Bearer <your_token>`.
- **Debug mode and logs:** To see more detail from MCP and Claude Desktop, enable debug logging: **Claude Desktop → Settings → Developer** and turn on **Debug mode**. To open the log file: **Claude Desktop → Developer → View logs** (or **Open log file**). Check the logs for connection errors, missing tokens, or server startup failures.
- **Server-side logging (LOG_LEVEL):** 
For Claude Desktop, server logs appear in Settings → Developer → View logs.

    To get more verbose logs from the Appcircle MCP server itself, set the `LOG_LEVEL` environment variable to `DEBUG`. In Claude Desktop config (stdio), add it to the `env` block. Example:

    ```json
    "appcircle": {
    "command": "/path/to/appcircle-mcp",
    "args": [],
    "env": {
        "APPCIRCLE_ACCESS_TOKEN": "ac_your_token_here",
        "LOG_LEVEL": "DEBUG"
    }
    }
    ```

---

## Claude Code (CLI)

[Claude Code](https://docs.claude.com/en/docs/claude-code/mcp) is a CLI tool that supports MCP servers via the `claude mcp add` command. All four running modes work with Claude Code.

### Prerequisites

- **Claude Code** installed (`npm install -g @anthropic-ai/claude-code`)
- **Appcircle access token** → see [Obtaining a token](../appcircle_access_token.md)

---

### 1. Remote server (mcp.appcircle.io)

No local install. Claude Code connects to Appcircle's hosted MCP server and sends your token on each request.

```bash
claude mcp add appcircle https://mcp.appcircle.io \
--transport http \
--header "Authorization: Bearer appcircle_access_token"
```

---

### 2. Local (stdio)

Install the server as described in [Section 2 above](#2-local-stdio) (clone + `pip install .`), then add it to Claude Code.

Get the CLI path first:

```bash
which appcircle-mcp
```

Then add it (replace the path and token). The default transport is stdio, so no `--transport` flag is needed:

```bash
claude mcp add appcircle \
  --env APPCIRCLE_ACCESS_TOKEN=appcircle_access_token \
  -- /path/to/appcircle-mcp
```

**Optional:** Exclude toolsets:

```bash
claude mcp add appcircle \
  --env APPCIRCLE_ACCESS_TOKEN=appcircle_access_token \
  -- /path/to/appcircle-mcp --exclude report
```

---

### 3. Local (streamable-http)

Install and start the HTTP server as described in [Section 3 above](#3-local-streamable-http), then add it to Claude Code:

```bash
claude mcp add appcircle \
  --transport http \
  --header "Authorization: Bearer appcircle_access_token" \
  -- http://localhost:8000
```

---

### 4. Local (Docker)

Build and run the container as described in [Section 4 above](#4-local-docker), then add it to Claude Code:

```bash
claude mcp add appcircle \
  --transport http \
  --header "Authorization: Bearer appcircle_access_token" \
  -- http://localhost:8000
```

---

### Managing servers in Claude Code

```bash
# List all configured MCP servers
claude mcp list

# Check details of the Appcircle server
claude mcp get appcircle

# Remove the Appcircle server
claude mcp remove appcircle

# Check server status (inside Claude Code)
/mcp
```

### Scopes

By default, `claude mcp add` saves the config to the **local** scope (current project only). Use `--scope` to change:

- `--scope local` — Current project only (default)
- `--scope project` — Shared with the team via `.mcp.json` in the project root (committed to version control)
- `--scope user` — Available across all your projects

Example (user scope):

```bash
claude mcp add appcircle \
  --transport http \
  --header "Authorization: Bearer appcircle_access_token" \
  --scope user \
  -- https://mcp.appcircle.io
```

### Troubleshooting (Claude Code)

- **Check server status:** Run `/mcp` inside Claude Code to see connected servers and their status.
- **401 Unauthorized:** Your access token may have expired (tokens are valid about 24 hours). Remove and re-add the server with a new token, or update the token in `~/.claude.json`. See [Obtaining a token](../appcircle_access_token.md#troubleshooting).
- **Debug logging:** Set `LOG_LEVEL=DEBUG` when adding the server to get verbose MCP server logs:

```bash
claude mcp add appcircle \
  --env APPCIRCLE_ACCESS_TOKEN=appcircle_access_token \
  --env LOG_LEVEL=DEBUG \
  -- /path/to/appcircle-mcp
```
