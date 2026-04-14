# Install Appcircle MCP Server in VS Code (GitHub Copilot)

## VS Code (GitHub Copilot)

### Prerequisites

- **VS Code** with **GitHub Copilot** (or Copilot Chat) installed (latest version recommended)
- **Appcircle access token** → see [Obtaining a token](../appcircle_access_token.md) for how to get one (Personal Access Key or API Keys)
- **Python 3.10+** (required only for local stdio install; see Section 2)

### Open the MCP config

VS Code reads MCP server configuration from `mcp.json` in one of two places:

- **User profile:** Open via **Command Palette** (Ctrl+Shift+P / Cmd+Shift+P) → **MCP: Open User Configuration**. Servers here are available in all workspaces.
- **Workspace:** **MCP: Open Workspace Folder MCP Configuration** or create `.vscode/mcp.json` in your project. Use this to share the config with your team via source control.

You can also run **MCP: Add Server** for a guided flow to add a server.

**Important:** VS Code uses a `"servers"` object (not `mcpServers`). Each server must have a `"type"` of `"stdio"` or `"http"`. After editing, save the file. Start or restart the server via **MCP: List Servers** if needed; on first use you may be prompted to trust the server.

---

You can use the Appcircle MCP Server in four ways. Each section below provides a `servers` entry you can add to `mcp.json`.

---

## 1. Remote server (mcp.appcircle.io)

No local install. VS Code connects to Appcircle's hosted MCP server and sends your token on each request.

Add this to your config (replace `your_access_token_here` with your token; see [Obtaining a token](../appcircle_access_token.md)):

```json
{
  "servers": {
    "appcircle": {
      "type": "http",
      "url": "https://mcp.appcircle.io",
      "headers": {
        "Authorization": "Bearer your_access_token_here"
      }
    }
  }
}
```

---

## 2. Local (stdio)

VS Code starts the server as a local subprocess (stdio).

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

Use this path in the next step (full path is recommended).

### VS Code setup

1. **Open** `mcp.json` (Command Palette → **MCP: Open User Configuration** or **MCP: Open Workspace Folder MCP Configuration**).

2. **Add the Appcircle server** (replace `PATH_FROM_WHICH_APPCIRCLE_MCP` with the path from the step above):

```json
{
  "servers": {
    "appcircle": {
      "type": "stdio",
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
  "type": "stdio",
  "command": "/Users/you/appcircle-mcp/venv/bin/appcircle-mcp",
  "args": [],
  "env": {
    "APPCIRCLE_ACCESS_TOKEN": "appcircle_access_token"
  }
}
```

3. **Optional:** Exclude toolsets (e.g. skip report tools). For the list of toolsets, see the [Toolsets](../../README.md#toolsets) section in the main README:

```json
"args": ["--exclude", "report"]
```

4. Save the config. Start or restart the server via **MCP: List Servers** if needed, and confirm the Appcircle tools are available in Copilot Chat.

---

## 3. Local (streamable-http)

You start the server yourself (HTTP), then VS Code connects to it.

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

### VS Code setup

1. **Open** `mcp.json` (Command Palette → **MCP: Open User Configuration** or **MCP: Open Workspace Folder MCP Configuration**).

2. **Add the Appcircle server** (replace `your_access_token_here` with your token):

```json
{
  "servers": {
    "appcircle": {
      "type": "http",
      "url": "http://localhost:8000",
      "headers": {
        "Authorization": "Bearer your_access_token_here"
      }
    }
  }
}
```

3. Save the config and confirm the Appcircle tools appear in Copilot Chat (start or restart the server via **MCP: List Servers** if needed).

---

## 4. Local (Docker)

Run the server in a Docker container (HTTP), then VS Code connects to it.

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

### VS Code setup

1. **Open** `mcp.json` (Command Palette → **MCP: Open User Configuration** or **MCP: Open Workspace Folder MCP Configuration**).

2. **Add the Appcircle server** (replace `your_access_token_here` with your token):

```json
{
  "servers": {
    "appcircle": {
      "type": "http",
      "url": "http://localhost:8000",
      "headers": {
        "Authorization": "Bearer your_access_token_here"
      }
    }
  }
}
```

3. Save the config and confirm the Appcircle tools appear in Copilot Chat (start or restart the server via **MCP: List Servers** if needed).

---

## Troubleshooting

- **Server not showing in VS Code:** Ensure the JSON is valid, the config file is in the right place (user `mcp.json` or `.vscode/mcp.json`), and each server has the correct `"type"` (`"stdio"` or `"http"`). Use **MCP: List Servers** to start or restart the server.
- **401 Unauthorized:** Your access token may have expired (tokens are valid about 10 hours). Generate a new one and update your config. See [Obtaining a token](../appcircle_access_token.md) and the [Troubleshooting section](../appcircle_access_token.md#troubleshooting) there.
- **Streamable-http / Docker:** Confirm the server is running (`http://localhost:8000/health`) and that your config includes the `Authorization` header with a valid token.
- **View logs:** Run **MCP: List Servers**, select the Appcircle server, and choose **Show Output** to view server logs.
- **Trust:** If you need to re-confirm trust, run **MCP: Reset Trust** from the Command Palette.
- **Avoid hardcoding secrets:** VS Code supports [input variables](https://code.visualstudio.com/docs/copilot/reference/mcp-configuration#_input-variables-for-sensitive-data) in `mcp.json` so you can be prompted for the token instead of storing it in the file.
- **Server-side logging (LOG_LEVEL):** To get more verbose logs from the Appcircle MCP server, set the `LOG_LEVEL` environment variable to `DEBUG`. In your config (stdio), add it to the `env` object:

```json
"appcircle": {
  "type": "stdio",
  "command": "/path/to/appcircle-mcp",
  "args": [],
  "env": {
    "APPCIRCLE_ACCESS_TOKEN": "appcircle_access_token",
    "LOG_LEVEL": "DEBUG"
  }
}
```
