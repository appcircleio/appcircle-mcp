# Install Appcircle MCP Server in Codex

## Codex (App)

### Prerequisites

- **Codex** (IDE/app) installed (latest version recommended)
- **Appcircle access token** → see [Obtaining a token](../appcircle_access_token.md) for how to get one (Personal Access Key or API Keys)

### Open the MCP config

Codex reads MCP server configuration from:

- **Global:** `~/.codex/config.toml` in your home directory (applies to all projects)
- **Project-level:** `.codex/config.toml` in your project root (trusted projects only)

You can edit these files directly, or in the Codex IDE: **Settings → Configuration → Open config.toml** from the gear menu.

After any config change, **fully restart Codex** (quit and reopen).

---

You can use the Appcircle MCP Server in four ways. Each section below provides a `[mcp_servers.appcircle]` block you can add to `~/.codex/config.toml` or `.codex/config.toml`.

---

## 1. Remote server (mcp.appcircle.io)

No local install. Codex connects to Appcircle's hosted MCP server and sends your token on each request.

Add this to your config (replace `your_access_token_here` with your token; see [Obtaining a token](../appcircle_access_token.md)):

```toml
[mcp_servers.appcircle]
url = "https://mcp.appcircle.io"

[mcp_servers.appcircle.http_headers]
Authorization = "Bearer your_access_token_here"
```

---

## 2. Local (stdio)

Codex starts the server as a local subprocess (stdio).

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

After installing, get the full path to the CLI:

```bash
which appcircle-mcp
```

Example outputs:

- **venv:** `/path/to/appcircle-mcp/venv/bin/appcircle-mcp`
- **user install:** `~/.local/bin/appcircle-mcp`
- **pyenv:** `~/.pyenv/shims/appcircle-mcp` (or use `pyenv which appcircle-mcp` for the real binary)

Use this exact path in the next step.

### Codex setup

1. **Open or create** `~/.codex/config.toml` or `.codex/config.toml`.

2. **Add the Appcircle server** (replace `PATH_FROM_WHICH_APPCIRCLE_MCP` with the path from the step above):

```toml
[mcp_servers.appcircle]
command = "PATH_FROM_WHICH_APPCIRCLE_MCP"
args = []

[mcp_servers.appcircle.env]
APPCIRCLE_ACCESS_TOKEN = "appcircle_access_token"
```

Example (venv in the repo):

```toml
[mcp_servers.appcircle]
command = "/Users/you/appcircle-mcp/venv/bin/appcircle-mcp"
args = []

[mcp_servers.appcircle.env]
APPCIRCLE_ACCESS_TOKEN = "appcircle_access_token"
```

3. **Optional:** Exclude toolsets (e.g. skip report tools). For the list of toolsets, see the [Toolsets](../../README.md#toolsets) section in the main README:

```toml
args = ["--exclude", "report"]
```

4. **Restart Codex** and confirm the Appcircle tools are available (e.g. in the MCP / tools panel).

---

## 3. Local (streamable-http)

You start the server yourself (HTTP), then Codex connects to it.

**Security note:** When running locally, the server should bind only to localhost (`127.0.0.1`) rather than all network interfaces (`0.0.0.0`). The default `--host` is `127.0.0.1`.

### Prerequisites

- **Python 3.10+** (and the server installed as in Section 2)
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

**Optional:** Exclude toolsets when starting the server. For the list of toolsets and exclusion options, see the [Toolsets](../../README.md#toolsets) section in the main README.

```bash
appcircle-mcp --transport streamable-http --host 127.0.0.1 --port 8000 --exclude report
```

### Codex setup

1. **Open or create** `~/.codex/config.toml` or `.codex/config.toml`.

2. **Add the Appcircle server** (replace `your_access_token_here` with your token; see [Obtaining a token](../appcircle_access_token.md)):

```toml
[mcp_servers.appcircle]
url = "http://localhost:8000"

[mcp_servers.appcircle.http_headers]
Authorization = "Bearer your_access_token_here"
```

3. **Restart Codex** and confirm the Appcircle tools appear.

---

## 4. Local (Docker)

Run the server in a Docker container (HTTP), then Codex connects to it.

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

### Codex setup

1. **Open or create** `~/.codex/config.toml` or `.codex/config.toml`.

2. **Add the Appcircle server** (replace `your_access_token_here` with your token; see [Obtaining a token](../appcircle_access_token.md)):

```toml
[mcp_servers.appcircle]
url = "http://localhost:8000"

[mcp_servers.appcircle.http_headers]
Authorization = "Bearer your_access_token_here"
```

3. **Restart Codex** and confirm the Appcircle tools appear.

---

## Troubleshooting

- **Server not showing in Codex:** Ensure the TOML is valid, the config file is in the right place (`~/.codex/config.toml` or `.codex/config.toml`), and you fully restarted Codex.
- **401 Unauthorized:** Your access token may have expired (tokens are valid about 10 hours). Generate a new one and update your config or environment. See [Obtaining a token](../appcircle_access_token.md) and the [Troubleshooting section](../appcircle_access_token.md#troubleshooting) there.
- **Streamable-http / Docker:** Confirm the server is running (`http://localhost:8000/health`) and that your config includes the `Authorization` header in `[mcp_servers.appcircle.http_headers]` with a valid token.
- **MCP settings:** You can also open the config via **Codex → Settings → Configuration → Open config.toml**; restart Codex after changes.
- **Server-side logging (LOG_LEVEL):** To get more verbose logs from the Appcircle MCP server, set the `LOG_LEVEL` environment variable to `DEBUG`. In your config (stdio), add it to the env table:

```toml
[mcp_servers.appcircle.env]
APPCIRCLE_ACCESS_TOKEN = "appcircle_access_token"
LOG_LEVEL = "DEBUG"
```

---

## Codex CLI

The Codex CLI supports MCP servers via the `codex mcp add` command. All four running modes work with the CLI. Configuration is stored in the same `config.toml` as the Codex app, so servers you add with the CLI are available in the app and vice versa.

### Prerequisites

- **Codex CLI** installed
- **Appcircle access token** → see [Obtaining a token](../appcircle_access_token.md)

---

### 1. Remote server (mcp.appcircle.io)

No local install. Codex CLI connects to Appcircle's hosted MCP server and sends your token on each request.

Export your token, then add the server:

```bash
export APPCIRCLE_ACCESS_TOKEN="appcircle_access_token"
codex mcp add appcircle --url https://mcp.appcircle.io --bearer-token-env-var=APPCIRCLE_ACCESS_TOKEN
```

---

### 2. Local (stdio)

Install the server as described in [Section 2 above](#2-local-stdio) (clone + `pip install .`), then add it to Codex CLI.

Get the CLI path first:

```bash
which appcircle-mcp
```

Then add it (replace the path and token):

```bash
codex mcp add appcircle \
  --env APPCIRCLE_ACCESS_TOKEN=appcircle_access_token \
  -- /path/to/appcircle-mcp
```

**Optional:** Exclude toolsets:

```bash
codex mcp add appcircle \
  --env APPCIRCLE_ACCESS_TOKEN=appcircle_access_token \
  -- /path/to/appcircle-mcp --exclude report
```

---

### 3. Local (streamable-http)

Install and start the HTTP server as described in [Section 3 above](#3-local-streamable-http), then add it to Codex CLI:

```bash
export APPCIRCLE_ACCESS_TOKEN="appcircle_access_token"
codex mcp add appcircle --url http://localhost:8000 --bearer-token-env-var=APPCIRCLE_ACCESS_TOKEN
```

---

### 4. Local (Docker)

Build and run the container as described in [Section 4 above](#4-local-docker), then add it to Codex CLI:

```bash
export APPCIRCLE_ACCESS_TOKEN="appcircle_access_token"
codex mcp add appcircle --url http://localhost:8000 --bearer-token-env-var=APPCIRCLE_ACCESS_TOKEN
```

---

### Managing servers in Codex CLI

```bash
# List all configured MCP servers
codex mcp list

# Check details of the Appcircle server
codex mcp get appcircle

# Remove the Appcircle server
codex mcp remove appcircle
```

In the Codex TUI, use `/mcp` to see active MCP servers and their status.

---

### Troubleshooting (Codex CLI)

- **Check server status:** Run `codex mcp list` or `/mcp` in the Codex TUI to see configured servers and their status.
- **401 Unauthorized:** Your access token may have expired (tokens are valid about 10 hours). Remove and re-add the server with a new token: `codex mcp remove appcircle` then `codex mcp add appcircle ...` with the new token. See [Obtaining a token](../appcircle_access_token.md#troubleshooting).
- **Debug logging:** Set `LOG_LEVEL=DEBUG` when adding the server to get verbose MCP server logs (stdio only):

```bash
codex mcp add appcircle \
  --env APPCIRCLE_ACCESS_TOKEN=appcircle_access_token \
  --env LOG_LEVEL=DEBUG \
  -- /path/to/appcircle-mcp
```
