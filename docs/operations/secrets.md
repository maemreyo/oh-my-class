# Production secrets

Production deployments must inject secrets through the deployment secret manager, for example Vault, Doppler, cloud secret stores, or CI/CD encrypted variables. The env-var interface stays unchanged: deployment templates set the same variable names used by local development, but real values are injected at runtime.

The gateway refuses to start when `ENV=production` or `OMC_ENVIRONMENT=production` and any tracked secret is empty, all-zero, or equal to a known development default. The guarded variables are:

- `POSTGRES_PASSWORD`
- `REDIS_AUTH`
- `LANGFUSE_ENCRYPTION_KEY`
- `LANGFUSE_NEXTAUTH_SECRET`
- `CLICKHOUSE_PASSWORD`
- `MINIO_ROOT_PASSWORD`

`.env.production` is a template only. It must contain placeholders, not real secrets, and every variable above must be overridden by the deployment environment.

## Langfuse encryption key rotation

1. Generate a new high-entropy `LANGFUSE_ENCRYPTION_KEY` outside the repository.
2. Store it in the deployment secret manager under the production environment.
3. Schedule a maintenance window, because encrypted Langfuse payloads must be readable with the active key during rotation.
4. Deploy with both old and new key material according to the Langfuse rotation procedure for the running version, re-encrypt stored values, then remove the old key.
5. Restart the gateway and Langfuse services. Startup must fail if the new key is empty, all-zero, or a known default.
