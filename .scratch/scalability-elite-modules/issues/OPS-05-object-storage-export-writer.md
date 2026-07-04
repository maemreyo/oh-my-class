# [OPS-05] Object-storage export writer — S3/MinIO behind the existing `TeachingPackExportWriter` Protocol

Status: TODO
Labels: ops, storage
ADR: 034
Depends on: none

## Context

Exports (rendered HTML previews + GIFT/H5P/QTI/Anki/flashcard files) are written to the **local filesystem** today: `FileSystemTeachingPackExportWriter` (`services/gateway/teaching_pack_export_writer.py:39`) writes under `base_dir = .scratch/pipeline-v2/artifacts/exports/<run_id>/` (:41) and returns local paths (`str(export_path)` :64,68,71). This is single-node: at the mid-scale target (~5,000 packs/day, a dedicated worker fleet in OPS-06, zero-downtime redeploys in OPS-08) local paths are wrong — a preview written by worker A can't be served by API instance B, and paths vanish on redeploy.

The good news: the **seam already exists.** `TeachingPackExportWriter` is a `Protocol` (:28, `async def write_exports(run_id, state) -> list[str]`). Per ADR-034 §3 we add an **object-storage implementation behind that Protocol**, env-mapped (dev=fs, staging/prod=object), serve previews/exports via **signed URLs**, and **store object keys in the DB, not local paths**. MinIO (S3-compatible) already runs in `infra/compose/docker-compose.yml` (`minio` service :145, creds `minio`/`${MINIO_ROOT_PASSWORD}`) — it currently backs Langfuse's S3 upload, so the S3 wiring and bucket pattern are already proven in-compose.

The export writer has three payload paths to preserve exactly: inline assessment formats (`_INLINE_ASSESSMENT_FORMATS = {gift,h5p,qti}` :89, written via `write_bytes`), subprocess formats (`_SUBPROCESS_EXPORT_FORMATS = {anki_apkg,flashcard_tsv}` :90, produced by the Node CLI `packages/exporters/dist/cli.js` into `export_dir` :175-251), and rendered HTML per approved snapshot (:61-64). The Node CLI writes to a directory on disk — that interaction must be handled (write-to-temp then upload).

## Scope

- [ ] **`ObjectStorageTeachingPackExportWriter`** implementing the `TeachingPackExportWriter` Protocol — same `write_exports(run_id, state) -> list[str]` signature and the same approved-snapshot / assessment-format / subprocess-format logic, but writing to S3/MinIO and returning **object keys** (or `s3://bucket/key`), not filesystem paths. Reuse the existing pure helpers (`_approved_snapshot_ids`, `_rendered_snapshots`, `_assessment_formats`, `_subprocess_formats`, `_assessment_payload`) unchanged.
- [ ] **Handle the Node subprocess path** — the CLI (`_node_export` :175) writes a file into `export_dir` on local disk and returns its path. For object storage: give the CLI a temp dir, then upload the produced file to S3 and return the key; clean up the temp dir. Preserve the existing fail-closed behavior (`ExportAdapterError` on non-zero exit / timeout / missing build — :186-249). Do NOT change the CLI contract.
- [ ] **Env-mapped selection** — a factory picks the writer by environment: `development` → `FileSystemTeachingPackExportWriter` (unchanged), `staging`/`production` → `ObjectStorageTeachingPackExportWriter`. Mirror the existing store-factory pattern at `services/gateway/main.py:167-172` (`if environment in ("staging","production")` → Postgres store, else dev store). Wire the export writer selection the same way where it is constructed.
- [ ] **Store keys in DB, not paths** — persist returned object keys on the run/artifact record (or a dedicated export-artifacts table) instead of local paths. Migrate the field/semantics so downstream readers fetch by key. (Backfill of existing local paths is OPS-14's job — note the coupling; here, make new writes key-based.)
- [ ] **Serve via signed URLs** — preview/export retrieval endpoints must return **time-bounded signed URLs** to the object, not stream from local disk. Find the current preview/download path (`teaching_pack_previews` router, `services/gateway/routers/`) and add signed-URL issuance for object-backed exports. Signed-URL TTL env-tunable; short by default.
- [ ] **Fail-closed on write error** — an upload failure must raise (like the FS writer raises `ExportAdapterError`), never silently succeed with a missing object or fall back to local disk in prod. The run's export step fails visibly so healing/escalation handles it — consistent with the existing writer's fail-closed posture (`_node_export` never falls back to HTML :183).
- [ ] **Bucket / lifecycle hooks** — create/expect a dedicated exports bucket (separate from Langfuse's). Leave object-lifecycle/TTL *rules* to OPS-07 but ensure keys are namespaced (`exports/<run_id>/<file>`) so lifecycle rules and retention can target them.

## Acceptance

- In staging/prod, a completed run writes all its export artifacts (HTML previews, gift/h5p/qti, anki/flashcard) to S3/MinIO; the DB stores object keys, not `.scratch/...` paths.
- A preview/export is retrievable by any API instance via a signed URL (no local-disk dependency); the URL expires after its TTL.
- Dev is unchanged: `FileSystemTeachingPackExportWriter` under `.scratch/pipeline-v2/artifacts/exports/` still used; existing FS-writer tests pass.
- An induced S3 upload failure raises `ExportAdapterError` and fails the export step (fail-closed) — it does not write a local file or return a dangling key.
- The Node subprocess formats (anki_apkg, flashcard_tsv) still produce identical bytes, now uploaded to S3; CLI contract unchanged.
- Verified against the real MinIO in compose (real object round-trip + real signed-URL fetch), not a mocked S3 client.

## References

- `services/gateway/teaching_pack_export_writer.py` — `TeachingPackExportWriter` Protocol :28, `FileSystemTeachingPackExportWriter` :39 (`base_dir=.scratch/pipeline-v2/artifacts/exports` :41), `write_exports` :44, helpers `_approved_snapshot_ids` :75 / `_rendered_snapshots` :82 / `_assessment_formats` :94 / `_subprocess_formats` :106 / `_assessment_payload` :160, `_INLINE_ASSESSMENT_FORMATS` :89, `_SUBPROCESS_EXPORT_FORMATS` :90, `_node_export` :175, `ExportAdapterError` :17.
- `services/gateway/main.py:167-172` — env-mapped store factory (`open_teaching_pack_store` vs `get_development_store`) — the pattern to mirror for writer selection.
- `packages/exporters/dist/cli.js` — Node export CLI bridge (contract: stdin JSON `{format,run_id,artifacts,output_dir}`, stdout `{path}`|`{error}`).
- `infra/compose/docker-compose.yml` — `minio` service :145 (S3 endpoint `http://minio:9000`, creds), Langfuse S3 env :79-88 (proven S3 wiring).
- `services/gateway/routers/teaching_pack_previews.py` (preview/download endpoints — add signed-URL issuance).
- ADR-034 §3 (exports → object storage behind the Protocol; env-mapped; signed URLs; keys in DB).

## Implementation notes

- The `write_exports` return type is `list[str]`; keep it, but define the string as an **object key** (or `s3://` URI) in the object impl and make the DB/serving layer key-aware. Don't leak `s3://` vs bare-key ambiguity — pick one representation and document it.
- Reuse the existing pure payload builders (`_gift_payload`, `_h5p_payload`, `_qti_payload`, `_assessment_payload`) verbatim — only the *sink* changes (bytes → S3 put instead of `write_bytes`). This keeps the object writer thin and the export semantics identical.
- For the Node path, prefer `tempfile.TemporaryDirectory()` as `output_dir`, upload the returned `path`, then let the context manager clean up — preserving the timeout/exit-code fail-closed handling already in `_node_export`.
- Signed URLs: generate with the S3 client's presign; do not proxy bytes through the API for large Anki packages. TTL short (minutes) and env-tunable; regenerate on demand.
- Keep the S3 client construction in one small module so OPS-07 (lifecycle rules) and OPS-14 (backfill) reuse the same client/bucket config; read endpoint/creds from env (matching the compose MinIO vars).
- Live-path proof (ADR-032): the acceptance test must round-trip a real object through MinIO and fetch it back via the signed URL — not assert on a mocked put_object call.
