# BE-8827 — ENV Schema Audit & Naming Convention: appcircle-mcp

Linear: https://linear.app/appcircle/issue/BE-8827/env-schema-audit-and-naming-convention-all-microservices
Parent: PL-158 (env schema audit) / same project as PL-123 (config-client libraries)
Python config-client hub spec: https://github.com/appcircleio/ac-lib-python-config/blob/master/docs/tasks/PL-123/spec.md

`appcircle-mcp` isn't in BE-8827's original per-service table (that table only lists .NET
services), but the same two things apply here: bring its env vars in line with
`doc/internal-doc/docs/development/backend/conventions/environment-variables.md`, and adopt the
Config Service client for Appcircle's own hosted deployment — same as `ac-codepush-service`/
`ac-web-event` did for PL-123.

## Critical constraint this repo has that the other two didn't

`appcircle-mcp-server` is a **public, MIT-licensed, customer-installed** package — not solely an
internally-deployed service. Per `docs/installation_guides/*`, customers `git clone` +
`pip install .` this repo directly onto their own machines (stdio and local-streamable-http
install modes); only the "remote server (mcp.appcircle.io)" mode is Appcircle's own hosted
deployment. `appcircle-config-client` lives on the private Nexus registry
(`nexus.appcircle.io/repository/pypi-hosted`), unreachable from a customer's machine — making it a
**hard** dependency would break `pip install .` for every customer. Confirmed with the user before
touching `pyproject.toml`.

**Resolution:** `appcircle-config-client` is an **optional** dependency group
(`pip install ".[hosted]"`), and `server.py`'s `_bootstrap_hosted_config()` is a no-op — it doesn't
even attempt the import — unless `AC_CONFIG_SERVICE_URL` is set. A customer's install never sets
that var and never installs the `hosted` extra, so nothing changes for them. Only Appcircle's own
`mcp.appcircle.io` deployment (wherever that's actually built — not necessarily this repo's own
example `Dockerfile`, which was deliberately left untouched; see "Out of scope" below) sets both.

## Env var mapping (current → new, per environment-variables.md)

| Old | New | Source |
| --- | --- | --- |
| `APPCIRCLE_ACCESS_TOKEN` | `AC_API_ACCESS_TOKEN` | `server.py` `main()` (stdio only) |
| `APPCIRCLE_API_URL` | `AC_API_EXTERNAL_URL` | `server.py` `main()` |
| `APPCIRCLE_MCP_ALLOWED_HOST` | `AC_ALLOWED_HOST` | `server.py` `main()`, `_run_http()` |
| `APPCIRCLE_MCP_PORT` | `AC_PORT` | `server.py` `_parse_args()` |
| `LOG_LEVEL` | `AC_LOG_MIN_LEVEL` | `core/logger.py` `setup_logging()` |
| `APPCIRCLE_EXCLUDED_TOOLSETS` | `AC_EXCLUDED_TOOLSETS` | `server.py` `_parse_args()` |
| `AC_MCP_ENABLE_WRITE_TOOLS` | `AC_WRITE_TOOLS_ENABLED` | `server.py` `_parse_args()` |

Every one of these reads the new name first, falling back to the old name — the exact dual-name
pattern the rest of BE-8827 uses everywhere else (see `Appcircle.Core`'s BE-8827 commits, e.g.
`RijndaelHelper.cs`'s `AC_RIJNDAEL_KEY`/`ASPNETCORE_RIJNDAEL_KEY` fallback) — a customer's existing
config (documented in this repo's own README and every installation guide) keeps working
unchanged.

`AC_MCP_ENABLE_WRITE_TOOLS` (already `AC_`-prefixed before this task) is renamed too: it carries a
redundant "MCP" component — this service's own name — which `environment-variables.md`'s component
rule forbids ("a service never prefixes a variable with its own component"). Both names work.

## Context/secret reference confirmation (envdef.yaml, hosted deployment only)

- `AC_API_EXTERNAL_URL` → `${context:api_external_url}` — **confirmed**, an existing derived
  context value (`deployment-context-and-service-naming.md`).
- `AC_ALLOWED_HOST` → `${context:mcp_external_url}` — **not yet in `contextdef.yaml`**, no
  existing context input for this server's own public hostname. Flagged, not invented-as-if-real.
- `AC_API_ACCESS_TOKEN` is **not** in `envdef.yaml` at all: the hosted deployment only runs
  `--transport streamable-http`, where every request carries its own caller-supplied bearer token
  (`TokenExtractionMiddleware`) — the server itself never holds one static token, so there's
  nothing for Config Service to resolve here.
- `service: appcircle-mcp` — proposed, not confirmed. Per "Service Naming" in
  `deployment-context-and-service-naming.md`, a brand-new service's real identity is decided once
  at onboarding (Compose `services.list` / Helm ServiceAccount name), not derivable from docs.

## Known, accepted limitation: `AC_LOG_MIN_LEVEL` isn't actually resolved in time

`core/logger.py`'s `logger = setup_logging()` runs at **module import time** (`from .core.logger
import logger` at the top of `server.py`, evaluated before `main()` — and therefore before
`_bootstrap_hosted_config()` — ever runs). Every other env var `_bootstrap_hosted_config()` needs
to precede is read from inside a function body (`main()`/`_parse_args()`/`_run_http()`), which
Python only evaluates when that function is *called* — so calling `_bootstrap_hosted_config()` as
the first statement in `main()` is sufficient for all of them except this one.

Fixing this properly would mean deferring `server.py`'s own top-level imports (`.mcp_instance`,
`.core.logger`, `.core.auth`) behind `main()`, which collides with `@mcp.custom_route("/health",
...)` and `TokenExtractionMiddleware` being defined at module scope, unconditionally, using `mcp`
imported at the top. That's a materially bigger restructure of a live, customer-facing module for
a purely cosmetic outcome (the hosted deployment's log verbosity doesn't reflect the
Config-Service-resolved value for one process; it falls back to whatever raw env/default was
present at import time — nothing functional breaks). Not done here; documented in
`_bootstrap_hosted_config()`'s own docstring and `core/logger.py`'s comment instead of silently
shipping a subtly-broken resolution.

## Out of scope

- The actual Docker image/deployment manifest for `mcp.appcircle.io` — this repo's own `Dockerfile`
  is described as an "example" and is very plausibly also used by customers who self-host via
  Docker (a documented install path), so it was deliberately left untouched: it already behaves
  correctly by construction (no `[hosted]` extra installed → `_bootstrap_hosted_config()` no-ops
  unless someone explicitly sets `AC_CONFIG_SERVICE_URL`, which a customer image never would).
  Wiring the *real* hosted image (wherever it's actually built) to install `.[hosted]` with a
  Nexus `--extra-index-url` and set `AC_CONFIG_SERVICE_URL`/`AC_CONFIG_CREDENTIAL_SOURCE` is
  infra-side, not discoverable or safe to guess at from this repo alone.
- Adding `mcp_external_url` (or whatever the confirmed name turns out to be) to `contextdef.yaml` —
  a `Appcircle.ConfigService` change, a different repo.
