# Install Appcircle MCP Server in GitHub Copilot CLI

## GitHub Copilot CLI

### Prerequisites

- **GitHub Copilot CLI** installed and working in your terminal
- **Appcircle access token** → see [Obtaining a token](../appcircle_access_token.md) for how to get one (Personal Access Key or API Keys)
- For **local stdio / streamable-http** modes: **Python 3.10+**
- For **Docker** mode: **Docker** installed and running

### Open the MCP config

GitHub Copilot CLI reads MCP server configuration from:

- **User-level:** `~/.copilot/mcp-config.json`

This file is a JSON object with an `mcpServers` property. Each entry under `mcpServers` defines a server by name (for example, `appcircle`).

You can edit this file manually in your editor. After any change, **restart your Copilot CLI session** (exit and start a new session) so it reloads the configuration.

From an active Copilot CLI session, you can also use `/mcp add` for an interactive setup, but this guide focuses on **manual edits to `mcp-config.json`** so you can reproduce the setup across machines.

---

You can use the Appcircle MCP Server in four ways. Each section below provides an `mcpServers` entry you can add to `~/.copilot/mcp-config.json`.

---

## 1. Remote server (mcp.appcircle.io)

No local install. Copilot CLI connects to Appcircle's hosted MCP server and sends your token on each request.

Add this to your config (replace the token or use an environment variable interpolation):

```json
{
  "mcpServers": {
    "appcircle": {
      "type": "http",
      "url": "https://mcp.appcircle.io",
      "headers": {
        "Authorization": "Bearer ${APPCIRCLE_ACCESS_TOKEN}"
      }
    }
  }
}
```

- Replace `${APPCIRCLE_ACCESS_TOKEN}` with a suitable environment variable or a literal token string (for example, `"Bearer appcircle_access_token"`).
- For how to generate a token, see [Obtaining a token](../appcircle_access_token.md).

After saving `~/.copilot/mcp-config.json`, restart Copilot CLI and run `/mcp show` to verify that `appcircle` appears in the server list.

---

## 2. Local (stdio)

Copilot CLI starts the server as a local subprocess over stdio.

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

### Copilot CLI setup

1. Open `~/.copilot/mcp-config.json` in your editor.

2. Add the Appcircle server (replace `PATH_FROM_WHICH_APPCIRCLE_MCP` with the path from the step above):

```json
{
  "mcpServers": {
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

3. **Optional:** Exclude toolsets (for example, skip report tools). For the list of toolsets and exclusion options, see the [Toolsets](../../README.md#toolsets) section in the main README.

```json
"args": ["--exclude", "report"]
```

4. Restart Copilot CLI and run `/mcp show` to confirm the `appcircle` server is available.

---

## 3. Local (streamable-http)

You start the server yourself over HTTP, then Copilot CLI connects to it.

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

### Copilot CLI setup

1. Open `~/.copilot/mcp-config.json` in your editor.

2. Add the Appcircle server (replace `appcircle_access_token` with your token, or use `${APPCIRCLE_ACCESS_TOKEN}`):

```json
{
  "mcpServers": {
    "appcircle": {
      "type": "http",
      "url": "http://localhost:8000",
      "headers": {
        "Authorization": "Bearer ${APPCIRCLE_ACCESS_TOKEN}"
      }
    }
  }
}
```

3. Restart Copilot CLI and run `/mcp show` to confirm the `appcircle` server is listed.

---

## 4. Local (Docker)

Run the server in a Docker container (HTTP), then Copilot CLI connects to it.

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

The server listens on `http://localhost:8000`. The Copilot CLI client sends the token; no Appcircle-specific env vars are required inside the container unless you want to configure exclusions via environment variables.

**Optional:** Exclude toolsets by passing env when running. For the list of toolsets, see the [Toolsets](../../README.md#toolsets) section in the main README.

```bash
docker run -d --name appcircle-mcp -p 8000:8000 -e APPCIRCLE_EXCLUDED_TOOLSETS=report appcircle-mcp-server
```

### Copilot CLI setup

1. Open `~/.copilot/mcp-config.json` in your editor.

2. Add the Appcircle server (replace `appcircle_access_token` with your token, or use `${APPCIRCLE_ACCESS_TOKEN}`):

```json
{
  "mcpServers": {
    "appcircle": {
      "type": "http",
      "url": "http://localhost:8000",
      "headers": {
        "Authorization": "Bearer ${APPCIRCLE_ACCESS_TOKEN}"
      }
    }
  }
}
```

3. Restart Copilot CLI and run `/mcp show` to confirm the `appcircle` server appears.

---

## Troubleshooting

- **Server not showing in Copilot CLI:** Ensure the JSON is valid, the config file is in the right place (`~/.copilot/mcp-config.json`), and you restarted Copilot CLI. From a running session, use `/mcp show` to list configured servers and verify `appcircle` is present.
- **401 Unauthorized:** Your access token may have expired or be incorrect. Generate a new one and update your config. See [Obtaining a token](../appcircle_access_token.md) and the [Troubleshooting section](../appcircle_access_token.md#troubleshooting) there.
- **Streamable-http / Docker:** Confirm the server is running (`http://localhost:8000/health`) and that the client is sending `Authorization: Bearer <your_token>` in the request headers.
- **Interactive setup vs. manual config:** If `/mcp add` created an entry that does not work, compare it against the examples above and update `~/.copilot/mcp-config.json` manually.
- **Server-side logging (LOG_LEVEL):** To get more verbose logs from the Appcircle MCP server, set the `LOG_LEVEL` environment variable to `DEBUG`. For stdio mode, add it to the `env` block in your config; for HTTP / Docker, set it in the environment when starting the server.

