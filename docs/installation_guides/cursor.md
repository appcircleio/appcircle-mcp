# Install Appcircle MCP Server in Cursor IDE

## Cursor IDE

### Prerequisites

- **Cursor IDE** installed (latest version recommended)
- **Appcircle access token** → see [Obtaining a token](../appcircle_access_token.md) for how to get one (Personal Access Key or API Keys)

### Open the MCP config

Cursor reads MCP server configuration from:

- **Project-level:** `.cursor/mcp.json` in your project root (applies only to that project)
- **Global:** `~/.cursor/mcp.json` in your home directory (applies to all workspaces)

You can open or create these files directly, or use **Cursor → Settings → Tools & MCP** to add and edit MCP servers via the UI.

After any config change, **fully restart Cursor** (quit and reopen).

---

You can use the Appcircle MCP Server in four ways. Each section below provides an `mcpServers` entry you can add to `.cursor/mcp.json` or `~/.cursor/mcp.json`.

---

## 1. Remote server (mcp.appcircle.io)

No local install. Cursor connects to Appcircle's hosted MCP server and sends your token on each request.

Add this to your config (replace the token):

```json
{
  "mcpServers": {
    "appcircle": {
      "url": "https://mcp.appcircle.io",
      "headers": {
        "Authorization": "Bearer appcircle_access_token"
      }
    }
  }
}
```

---

## 2. Local (stdio)

Cursor starts the server as a local subprocess (stdio).

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

### Cursor setup

1. **Open or create** `.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global).

2. **Add the Appcircle server** (replace `PATH_FROM_WHICH_APPCIRCLE_MCP` with the path from the step above):

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

3. **Optional:** Exclude toolsets (e.g. skip report tools):

```json
"args": ["--exclude", "report"]
```

4. **Restart Cursor** and confirm the Appcircle tools are available (e.g. in the MCP / tools panel).

---

## 3. Local (streamable-http)

You start the server yourself (HTTP), then Cursor connects to it.

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

### Cursor setup

1. **Open or create** `.cursor/mcp.json` or `~/.cursor/mcp.json`.

2. **Add the Appcircle server** (replace `appcircle_access_token` with your token):

Using URL + headers (if supported by your Cursor version):

```json
{
  "mcpServers": {
    "appcircle": {
      "url": "http://localhost:8000",
      "headers": {
        "Authorization": "Bearer appcircle_access_token"
      }
    }
  }
}
```

Or using npx mcp-remote:

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

3. **Restart Cursor** and confirm the Appcircle tools appear.

---

## 4. Local (Docker)

Run the server in a Docker container (HTTP), then Cursor connects to it.

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

### Cursor setup

1. **Open or create** `.cursor/mcp.json` or `~/.cursor/mcp.json`.

2. **Add the Appcircle server** (replace `appcircle_access_token` with your token):

Using URL + headers:

```json
{
  "mcpServers": {
    "appcircle": {
      "url": "http://localhost:8000",
      "headers": {
        "Authorization": "Bearer appcircle_access_token"
      }
    }
  }
}
```

Or using npx mcp-remote:

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

3. **Restart Cursor** and confirm the Appcircle tools appear.

---

## Troubleshooting

- **Server not showing in Cursor:** Ensure the JSON is valid, the config file is in the right place (`.cursor/mcp.json` or `~/.cursor/mcp.json`), and you fully restarted Cursor.
- **401 Unauthorized:** Your access token may have expired (tokens are valid about 10 hours). Generate a new one and update your config. See [Obtaining a token](../appcircle_access_token.md) and the [Troubleshooting section](../appcircle_access_token.md#troubleshooting) there.
- **Streamable-http / Docker:** Confirm the server is running (`http://localhost:8000/health`) and that the client is sending `Authorization: Bearer <your_token>`.
- **Settings UI:** You can also add or edit MCP servers via **Cursor → Settings → Tools & MCP**; restart Cursor after changes.
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
