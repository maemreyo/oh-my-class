# [OPS-12] Config & secrets management

Status: TODO
Labels: ops, security
ADR: 034
Depends on: none

## Context

Configuration is read ad-hoc via scattered `os.getenv` across the codebase, and secret handling
is partial:

- `JWT_SECRET` is mandatory at the JWT layer (`services/gateway/auth/jwt_handler.py`) but the
  dev default in `.env.example:120` is `changeme-use-openssl-rand-base64-32` — a `changeme`-class
  value that is only guarded for a *subset* of secrets.
- `secrets_guard.py` (`services/gateway/secrets_guard.py`) is **prod-only** (returns early unless
  `ENV`/`OMC_ENVIRONMENT` in `{production, prod}`) and covers a fixed `SECRET_RULES` tuple
  (`POSTGRES_PASSWORD`, `REDIS_AUTH`, `LANGFUSE_*`, `CLICKHOUSE_PASSWORD`, `MINIO_ROOT_PASSWORD`).
  Notably **`JWT_SECRET` is NOT in `SECRET_RULES`**, so its `changeme` default is not rejected in
  prod. The guard also does not assert the *full required set* is present — a missing (empty) var
  only trips a rule if that var happens to be listed.
- Config values are `.env`-based with no single typed, validated model; there is no boot-time
  fail-fast on a missing/invalid config value, and no secret-manager integration for staging/prod.

At the north-star scale this is a reliability and security liability: a mistyped or missing config
should fail loudly at boot, not surface as a runtime error under load, and no `changeme` secret
should ever reach staging/prod.

## Scope

- [ ] Introduce **one validated `pydantic-settings` model** (e.g. `services/gateway/settings.py`)
      that types every config/secret the gateway + worker consume (DB URL, Redis, JWT_SECRET,
      Langfuse, ClickHouse, MinIO/object-storage, provider/LLM config, env name, worker mode,
      backpressure/budget knobs where env-driven). Typed fields with validators and explicit
      required-vs-optional. This becomes the single source of truth.
- [ ] **Replace scattered `os.getenv`** call sites with reads from the settings model. Add a
      guard test / lint that fails on new raw `os.getenv` in gateway app code (allowing the
      settings module itself). Inventory current call sites first (grep `os.getenv`,
      `os.environ`).
- [ ] **Boot-time fail-fast**: instantiate + validate the settings model at startup
      (`services/gateway/main.py`) before serving traffic; on any missing/invalid required value,
      refuse to boot with a clear, secret-free error naming the offending field(s).
- [ ] **Extend `secrets_guard`** to:
      - include **`JWT_SECRET`** (and any other auth/crypto secret) in the rejected-defaults set,
        with `changeme`-family defaults (`changeme`, `changeme-use-openssl-rand-base64-32`, etc.);
      - assert the **full required secret set is present** (empty/missing ⇒ reject), not just
        that listed vars aren't set to a known-bad default;
      - keep the existing production gate but ensure staging is also covered where secrets apply.
- [ ] **Secret manager in staging/prod**: integrate a secret manager (e.g. env injected from
      Vault/cloud secret store) so secrets are not committed and not sourced from a plaintext
      `.env` in deployed environments; dev keeps `.env`. Document the resolution order
      (secret manager > env > dev default, with dev defaults forbidden outside dev).
- [ ] **No secrets in logs**: ensure the settings model never logs raw secret values (use
      `SecretStr` / masked repr), and add a check that error messages / boot logs / traces do not
      emit secret values. Cross-check with PRIV-01's "never logged" requirement.

## Acceptance

- Booting with a missing required config value fails fast at startup with a clear error naming
  the field; no partial serving.
- In staging/prod, a `JWT_SECRET` (or any covered secret) left at a `changeme`-family default is
  **rejected** at boot by the extended `secrets_guard` — proven by a test.
- `secrets_guard` rejects an empty/missing required secret, not only known-bad defaults.
- A grep/guard test shows no new raw `os.getenv` in gateway app code outside the settings module.
- Logs/traces at boot and on error contain no raw secret values (masked repr proven by a test).

## References

- `services/gateway/secrets_guard.py` — `SECRET_RULES`, prod-only `validate_production_secrets`
  (JWT_SECRET currently absent from rules).
- `services/gateway/auth/jwt_handler.py` — `JWT_SECRET` mandatory usage.
- `.env.example:119-122` — `JWT_SECRET=changeme-...`, `JWT_ALGORITHM`, `JWT_EXPIRY_HOURS`.
- `services/gateway/main.py` — startup wiring (add settings validation here).
- ADR-034 decision 9.

## Implementation notes

- `pydantic-settings` `BaseSettings` with `SecretStr` for secrets gives typing + masking for free;
  its repr masks secrets, which directly satisfies the "no secrets in logs" bar.
- Keep the model additive: mirror existing env names so `.env` / compose keep working; the change
  is *how* they're read (typed + validated), not *what* they're called.
- `secrets_guard` and the settings validator are complementary: settings = "is it present and
  well-typed", guard = "is it a real secret, not a placeholder". Run both at boot.
- Coordinate the "no secrets in logs" clause with PRIV-01 (student data) — same logging-hygiene
  discipline, different data class.
