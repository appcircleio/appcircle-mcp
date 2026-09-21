# BE-8827 — Implementation plan: appcircle-mcp

## Steps

1. Re-audit `os.getenv`/`os.environ` usage across `src/` against current `main` (had moved since
   the original PL-123 research — new `AC_MCP_ENABLE_WRITE_TOOLS` var, etc.) before touching
   anything.
2. Confirmed the customer-install constraint (see spec.md) with the user before adding
   `appcircle-config-client` to `pyproject.toml` at all — this is the one repo among the three
   PL-123/BE-8827 consumers where a hard dependency would be a real regression, not just a design
   nicety.
3. Add `appcircle-config-client` under `[project.optional-dependencies].hosted` (not a plain
   dependency).
4. Add `envdef.yaml` at the repo root — every var that's genuinely resolvable per Config Service's
   existing `contextdef.yaml`/secret model, clearly flagging the ones that aren't yet (see spec.md).
5. Add `_bootstrap_hosted_config()` to `server.py`: no-ops unless `AC_CONFIG_SERVICE_URL` is set,
   fails loudly (clear message, not a raw traceback) if set but the `hosted` extra isn't installed,
   or if the resolve itself fails. Called as the first statement in `main()`.
6. Rename every env var per the mapping table in spec.md — new `AC_`-prefixed name checked first,
   old name kept as a fallback (same dual-name pattern the rest of BE-8827 uses).
7. Update README.md's env var table (new / original columns) and add tests for
   `_bootstrap_hosted_config()` (no-op, missing-extra failure, successful resolve via a
   `sys.modules`-injected fake `appcircle_config_client`, resolve-failure path).
8. Verify: full `pytest test/unit/` suite green (711 tests - includes the 4 new
   `_bootstrap_hosted_config()` tests and a pre-existing test fixed along the way, see below).
9. Single commit once verified.

## A pre-existing test needed fixing, not just the new code

`test_invalid_port_env_falls_back_to_default` asserted the literal string `"APPCIRCLE_MCP_PORT"`
appeared in the warning log. The port-parsing rewrite (checking `AC_PORT` first) initially dropped
the variable name from that message entirely - a real regression, not a pre-existing failure like
the ones seen in the Node repos. Fixed by tracking which of the two var names was actually set and
naming it in the warning, rather than loosening the test's assertion.

## Explicitly not done here (see spec.md's "Out of scope")

- The real `mcp.appcircle.io` deployment's Docker image / manifest.
- Adding `mcp_external_url` to `Appcircle.ConfigService`'s `contextdef.yaml`.
- Fixing `AC_LOG_MIN_LEVEL`'s import-time-read limitation (would need restructuring `server.py`'s
  own module-level route/middleware definitions - see spec.md).
