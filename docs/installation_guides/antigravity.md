# Install Appcircle MCP Server in Antigravity IDE

## Antigravity IDE

### Prerequisites

- **Antigravity IDE** installed (latest version recommended)
- **Appcircle access token** → see [Obtaining a token](../appcircle_access_token.md) for how to get one (Personal Access Key or API Keys)
- **Node.js** (required for the remote and HTTP options below; Antigravity uses `npx mcp-remote` to connect)
- **Python 3.10+** (required only for local stdio install; see Section 2)

### Open the MCP config

Antigravity reads MCP server configuration from:

- **macOS/Linux:** `~/.gemini/antigravity/mcp_config.json`
- **Windows:** `C:\Users\<USERNAME>\.gemini\antigravity\mcp_config.json`

To open the config: in the **Agent Panel** (right side), click the **"..."** (three dots) at the top → **Manage MCP Servers** → **View raw config**.

You can also edit the file directly on disk.

After any config change, save the file. The editor may auto-initialize; if tools don't appear, toggle the server off and on in **Manage MCP Servers**, or restart Antigravity.

**Important:** When using a local binary (Section 2), use the **absolute path** to the command (e.g. from `which appcircle-mcp`). Relative paths often cause "Error Calling Initialize: EOF".

---

You can use the Appcircle MCP Server in four ways. Each section below provides an `mcpServers` entry you can add to `mcp_config.json`.

---

## 1. Remote server (mcp.appcircle.io)

No local install. Antigravity connects to Appcircle's hosted MCP server and sends your token on each request via `npx mcp-remote`.

Add this to your config (replace `appcircle_access_token` with your token; see [Obtaining a token](../appcircle_access_token.md)):

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

Antigravity starts the server as a local subprocess (stdio).

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

**Use this exact absolute path** in the next step. Do not use a relative path (e.g. `./venv/bin/appcircle-mcp`); Antigravity does not resolve relative paths and that often causes "Error Calling Initialize: EOF".

### Antigravity setup

1. **Open** `mcp_config.json` (via **Manage MCP Servers** → **View raw config** or edit the file directly).

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

4. Save the config and confirm the Appcircle tools are available (toggle the server in **Manage MCP Servers** or restart Antigravity if needed).

---

## 3. Local (streamable-http)

You start the server yourself (HTTP), then Antigravity connects to it via `npx mcp-remote`.

**Security note:** When running locally, the server should bind only to localhost (`127.0.0.1`) rather than all network interfaces (`0.0.0.0`). The default `--host` is `127.0.0.1`.

### Prerequisites

- **Python 3.10+** (and the server installed as in Section 2)
- **Appcircle access token** → see [Obtaining a token](../appcircle_access_token.md)
- **Node.js** (for `npx mcp-remote`)

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

### Antigravity setup

1. **Open** `mcp_config.json` (via **Manage MCP Servers** → **View raw config** or edit the file directly).

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

3. Save the config and confirm the Appcircle tools appear (toggle the server or restart Antigravity if needed).

---

## 4. Local (Docker)

Run the server in a Docker container (HTTP), then Antigravity connects to it via `npx mcp-remote`.

### Prerequisites

- **Docker**
- **Appcircle access token** → see [Obtaining a token](../appcircle_access_token.md)
- **Node.js** (for `npx mcp-remote`)

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

### Antigravity setup

1. **Open** `mcp_config.json` (via **Manage MCP Servers** → **View raw config** or edit the file directly).

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

3. Save the config and confirm the Appcircle tools appear (toggle the server or restart Antigravity if needed).

---

## Troubleshooting

- **Server not showing in Antigravity:** Ensure the JSON is valid (no missing commas or braces), the config file is in the correct location (`~/.gemini/antigravity/mcp_config.json` on macOS/Linux), and you saved the file. Toggle the server off and on in **Manage MCP Servers**, or restart Antigravity.
- **"Error Calling Initialize: EOF":** This often happens when the `command` for a local server (Section 2) uses a **relative path**. Use the full absolute path from `which appcircle-mcp` (e.g. `/Users/you/appcircle-mcp/venv/bin/appcircle-mcp`).
- **401 Unauthorized:** Your access token may have expired (tokens are valid about 10 hours). Generate a new one and update your config. See [Obtaining a token](../appcircle_access_token.md) and the [Troubleshooting section](../appcircle_access_token.md#troubleshooting) there.
- **Streamable-http / Docker:** Confirm the server is running (`http://localhost:8000/health`) and that your config sends `Authorization: Bearer <your_token>` in the `--header` argument.
- **Manage MCP Servers:** You can add or edit servers via **Agent Panel** → **"..."** → **Manage MCP Servers** → **View raw config**; save and toggle or restart after changes.
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
