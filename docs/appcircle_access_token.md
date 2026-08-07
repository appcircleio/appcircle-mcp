# Appcircle Access Token

To use the Appcircle MCP Server, you need an **Appcircle access token**. This token authenticates your requests to Appcircle’s APIs and is required for all running modes (stdio, streamable-http, or when connecting to the remote host).

This guide describes **two ways** to obtain an access token:

1. **Personal Access Key** — Best for individual use; inherits your user permissions.
2. **API Keys** — Best for automation and CI; scoped by organization and roles.

Choose the method that fits your use case. Both produce an `access_token` that you use as `APPCIRCLE_ACCESS_TOKEN`.

---

## Option 1: Personal Access Key (PAT)

A **Personal Access Key** is a secure credential you use to obtain a **Personal Access Token (PAT)**. The PAT inherits the permissions of your user account in the organization and is used to authenticate with Appcircle’s APIs.

**Important:** Personal Access Keys are **organization-specific**. You must create a separate key for each organization you use. A key created in the **Root** organization can also be used for **sub-organizations** by passing a `subOrganization` parameter when requesting the token.

### Step 1: Generate a Personal Access Key

1. Open the [Appcircle dashboard](https://my.appcircle.io) and go to **My Organization**.
2. In the left sidebar, open **Security**.
3. Find **Personal Access Key**.
4. Click **Generate Key**.
5. **Copy and store the key securely.** It is shown only once.

For full details, see the official docs:  
**[Personal Access Key Documentation](https://docs.appcircle.io/account/my-organization/security/personal-access-key)**

### Step 2: Exchange the Key for an Access Token

Use the key to request an access token from Appcircle’s auth API.

**Default (current organization):**

```bash
curl -X POST "https://auth.appcircle.io/auth/v3/token" \
  -H "accept: application/json" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "personalAccessKey=your_access_key" \
  -d "scope=openid,profile,email"
```

**With sub-organization (Root key only):**

```bash
curl -X POST "https://auth.appcircle.io/auth/v3/token" \
  -H "accept: application/json" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "personalAccessKey=your_access_key" \
  -d "scope=openid,profile,email" \
  -d "subOrganization=YOUR_SUB_ORG_ID"
```

Replace `your_access_key` with your Personal Access Key and `YOUR_SUB_ORG_ID` with the target sub-organization ID when applicable.

### Step 3: Use the Token

The response looks like:

```json
{"access_token":"xxxxx", ...}
```

Copy the `access_token` value and set it as `APPCIRCLE_ACCESS_TOKEN` in your environment or in your MCP client configuration.

---

## Option 2: API Keys

Appcircle **API Keys** let you create and manage tokens with specific organization and role scope. They are well-suited for automation, CI/CD, and when you want to limit permissions (e.g. read-only).

**Important:** When creating an API key, you choose **roles**. If you do **not** want the MCP server to perform write operations (e.g. triggering builds, changing settings), create an API key with **Viewer** (or read-only) access for the relevant modules. Granting broader roles gives the MCP server write access to those areas.

### Step 1: Create an API Key

1. In the Appcircle dashboard, go to **My Organization** → **Security** → **API Keys**.
2. Click **Create a New API Key**.
3. Enter a **name** and set an **expiry date** (default is 6 months; max 1 year). Name and expiry cannot be changed later.
4. Select the **Organization** and **Roles** for the key.
5. After creation, the **API key secret** is shown **only once**. Copy and store it securely. You can create another key with the same expiry later if needed, but the secret itself cannot be retrieved again.

Full instructions and screenshots:  
**[API Keys Documentation](https://docs.appcircle.io/account/my-organization/security/api-keys)**

### Step 2: Retrieve an Access Token Using the API Key

Use the API key **name**, **secret**, and **organization ID** to get an access token.

**Bash example:**

```bash
set -e

API_KEY_NAME=apikey1
API_KEY_SECRET='your_secret'
ROOT_ORGANIZATION_ID=your_orgID   # use root org ID for root org
SUB_ORGANIZATION_ID=your_orgID   # use sub-org ID for sub-org

echo "Retrieving access token for API key: $API_KEY_NAME"

response=$(curl --location 'https://auth.appcircle.io/auth/v1/api-key/token' \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode "name=$API_KEY_NAME" \
  --data-urlencode "secret=$API_KEY_SECRET" \
  --data-urlencode "organizationId=$SUB_ORGANIZATION_ID")

ACCESS_TOKEN=$(echo "$response" | jq -r '.access_token')

echo "Access token retrieved: $ACCESS_TOKEN"
```

- Replace `apikey1`, `your_secret`, and `your_orgID` with your API key name, secret, and the target organization ID (root or sub-org).
- For a **sub-organization**, use that org’s ID in `organizationId`. A key created in the root org can be used for sub-orgs if its roles allow it.

The response includes `access_token`. Use that value as `APPCIRCLE_ACCESS_TOKEN`.

### Step 3: Use the Token

Same as with the Personal Access Key: set the `access_token` value as `APPCIRCLE_ACCESS_TOKEN` in your environment or MCP client config.

---

## Using the Token with the MCP Server

- **stdio:** Set `APPCIRCLE_ACCESS_TOKEN` in the environment where the MCP server process runs (e.g. in your shell or in the config that launches `appcircle-mcp`).
- **streamable-http / remote host:** The client typically sends the token (e.g. `Authorization: Bearer <token>`) on each request; see [Installation guides](installation_guides/claude_applications.md) and the main [README](../README.md) for your client.

Token in environment (example):

```bash
export APPCIRCLE_ACCESS_TOKEN="your_access_token_here"
```

Then start the server as usual (e.g. `appcircle-mcp` or with your chosen transport and port).

---

## Renewing an Expired Token

Access tokens are valid for **about 24 hours** (see [Troubleshooting](#401-unauthorized-after-some-time)). Once a token expires, exchange your Personal Access Key or API key for a **new** access token, the same way you got the first one. The key/secret itself does not expire on this schedule: Personal Access Keys are valid for 1 year, and API Keys expire on their own configured expiry date (up to 1 year). You can repeat the exchange as many times as needed until the key itself expires.

1. **Get a new access token:**
   - If you used a **Personal Access Key**, repeat [Step 2: Exchange the Key for an Access Token](#step-2-exchange-the-key-for-an-access-token) with the same key.
   - If you used an **API Key**, repeat [Step 2: Retrieve an Access Token Using the API Key](#step-2-retrieve-an-access-token-using-the-api-key) with the same key name/secret.
2. **Copy the new `access_token`** from the response.
3. **Update `APPCIRCLE_ACCESS_TOKEN`** with the new value, in whichever place you set it for your setup (shell environment, `.env`, or your MCP client's configuration; see the client-specific [installation guides](installation_guides/claude_applications.md) for exact config locations).
4. **Restart the MCP server** (and/or reconnect your MCP client) so it picks up the new token. The server reads `APPCIRCLE_ACCESS_TOKEN` at startup and won't see an updated value until it's restarted.

---

## Troubleshooting

### 401 Unauthorized after some time

Access tokens obtained via **Personal Access Key** or **API Keys** are valid for **about 24 hours**. After that, they expire and API calls will return **401 Unauthorized**.

**What to do:** See [Renewing an Expired Token](#renewing-an-expired-token) above.
