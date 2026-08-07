# Install Appcircle MCP Server in Windsurf IDE

## Windsurf IDE

### Prerequisites

- **Windsurf IDE** installed → use the **latest version** of Windsurf for native HTTP support (`serverUrl` and `headers`) in Sections 1, 3, and 4
- **Appcircle access token** → see [Obtaining a token](../appcircle_access_token.md) for how to get one (Personal Access Key or API Keys)
- **Python 3.10+** (required only for local stdio install; see Section 2)

### Open the MCP config

Windsurf reads MCP server configuration from:

- **macOS:** `~/.codeium/windsurf/mcp_config.json` (or `~/.codeium/mcp_config.json`)
- **Linux:** `~/.codeium/windsurf/mcp_config.json` or `~/.config/Codeium/Windsurf/mcp_config.json`
- **Windows:** `%APPDATA%\Codeium\Windsurf\mcp_config.json`

To open the config: **Command Palette** (Ctrl+Shift+P / Cmd+Shift+P) → **Windsurf: MCP Marketplace → Gear icon next to installed MCPs**.

You can also edit the file directly on disk.

After any config change, save the file. Restart the server or toggle it in **MCP Marketplace**, or restart Windsurf if tools don't appear.

**Important:** When using a local binary (Section 2), use the **absolute path** to the command (e.g. from `which appcircle-mcp`) to avoid startup errors.

---

You can use the Appcircle MCP Server in four ways. Each section below provides an `mcpServers` entry you can add to `mcp_config.json`.

---

## 1. Remote server (mcp.appcircle.io)

No local install. Windsurf connects to Appcircle's hosted MCP server and sends your token on each request. Use the latest version of Windsurf for native HTTP support.

Add this to your config (replace `your_access_token_here` with your token; see [Obtaining a token](../appcircle_access_token.md)):

```json
{
  "mcpServers": {
    "appcircle": {
      "serverUrl": "https://mcp.appcircle.io",
      "headers": {
        "Authorization": "Bearer your_access_token_here"
      }
    }
  }
}
```

---

## 2. Local (stdio)

Windsurf starts the server as a local subprocess (stdio).

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

After installing, get the **absolute** path to the CLI:

```bash
which appcircle-mcp
```

Example outputs:

- **venv:** `/path/to/appcircle-mcp/venv/bin/appcircle-mcp`
- **user install:** `~/.local/bin/appcircle-mcp`
- **pyenv:** `~/.pyenv/shims/appcircle-mcp` (or use `pyenv which appcircle-mcp` for the real binary)

**Use this exact absolute path** in the next step to avoid startup errors.

### Windsurf setup

1. **Open** `mcp_config.json` (via **Windsurf: Configure MCP Servers** or **Manage MCPs → View raw config** or edit the file directly).

2. **Add the Appcircle server** (replace `PATH_FROM_WHICH_APPCIRCLE_MCP` with the **absolute path** from the step above):

```json
{
  "mcpServers": {
    "appcircle": {
      "command": "PATH_FROM_WHICH_APPCIRCLE_MCP",
      "args": [],
      "env": {
        "APPCIRCLE_ACCESS_TOKEN": "appcircle_access_token"
      }
    }
  }
}
```

Example (venv in the repo):

```json
"appcircle": {
  "command": "/Users/you/appcircle-mcp/venv/bin/appcircle-mcp",
  "args": [],
  "env": {
    "APPCIRCLE_ACCESS_TOKEN": "appcircle_access_token"
  }
}
```

3. **Optional:** Exclude toolsets (e.g. skip report tools). For the list of toolsets, see the [Toolsets](../../README.md#toolsets) section in the main README.

```json
"args": ["--exclude", "report"]
```

4. Save the config and confirm the Appcircle tools are available (restart the server in **Manage MCPs** or restart Windsurf if needed).

---

## 3. Local (streamable-http)

You start the server yourself (HTTP), then Windsurf connects to it.

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

### Windsurf setup

1. **Open** `mcp_config.json` (via **Windsurf: Configure MCP Servers** or **Manage MCPs → View raw config** or edit the file directly).

2. **Add the Appcircle server** (replace `your_access_token_here` with your token; use the latest Windsurf for native HTTP):

```json
{
  "mcpServers": {
    "appcircle": {
      "serverUrl": "http://localhost:8000",
      "headers": {
        "Authorization": "Bearer your_access_token_here"
      }
    }
  }
}
```

3. Save the config and confirm the Appcircle tools appear (restart the server or restart Windsurf if needed).

---

## 4. Local (Docker)

Run the server in a Docker container (HTTP), then Windsurf connects to it.

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

### Windsurf setup

1. **Open** `mcp_config.json` (via **Windsurf: Configure MCP Servers** or **Manage MCPs → View raw config** or edit the file directly).

2. **Add the Appcircle server** (replace `your_access_token_here` with your token; use the latest Windsurf for native HTTP):

```json
{
  "mcpServers": {
    "appcircle": {
      "serverUrl": "http://localhost:8000",
      "headers": {
        "Authorization": "Bearer your_access_token_here"
      }
    }
  }
}
```

3. Save the config and confirm the Appcircle tools appear (restart the server or restart Windsurf if needed).

---

## Troubleshooting

- **Server not showing in Windsurf:** Ensure the JSON is valid (no missing commas or braces), the config file is in the correct location (`~/.codeium/windsurf/mcp_config.json` on macOS/Linux), and you saved the file. Restart the server via **Manage MCPs** or restart Windsurf.
- **Startup / init errors:** When using a local binary (Section 2), use the full **absolute path** from `which appcircle-mcp` for the `command`; relative paths often cause initialization failures.
- **401 Unauthorized:** Your access token may have expired (tokens are valid about 24 hours). Generate a new one and update your config. See [Obtaining a token](../appcircle_access_token.md) and the [Troubleshooting section](../appcircle_access_token.md#troubleshooting) there.
- **Streamable-http / Docker:** Confirm the server is running (`http://localhost:8000/health`) and that your config includes the `Authorization` header with a valid token. Use the latest version of Windsurf for native HTTP support.
- **Manage MCPs:** You can add or edit servers via **Windsurf: Configure MCP Servers** or **Windsurf Settings → Manage MCPs → View raw config**; save and restart the server or Windsurf after changes.
- **Server-side logging (LOG_LEVEL):** To get more verbose logs from the Appcircle MCP server, set the `LOG_LEVEL` environment variable to `DEBUG`. In your config (stdio), add it to the `env` block:

```json
"appcircle": {
  "command": "/path/to/appcircle-mcp",
  "args": [],
  "env": {
    "APPCIRCLE_ACCESS_TOKEN": "appcircle_access_token",
    "LOG_LEVEL": "DEBUG"
  }
}
```
