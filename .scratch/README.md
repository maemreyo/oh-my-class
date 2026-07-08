# `.scratch/` conventions

Working notes and issue files for in-flight design/build work. Not shipped, not CI-gated.

## `status` frontmatter field

Each issue file's YAML frontmatter (`---\nkey: value\n---`) carries a `status` field with one of these values:

- `ready` / `ready-for-agent` — queued, not yet started.
- `deferred` — intentionally postponed, not abandoned.
- `done` — completed.
- `superseded` — replaced by a newer plan; kept only as historical record. Pair with a `superseded: <date>` field noting when, e.g.:

  ```yaml
  status: superseded
  created: 2026-06-24
  superseded: 2026-07-08
  ```

`created: <date>` (YYYY-MM-DD) is required alongside `status` — it's what `scripts/check_stale_scratch_issues.py` uses to flag issues that have sat `ready`/`ready-for-agent`/`deferred` for a long time and may deserve a `superseded` note instead.

See `.scratch/9router-integration/ISSUE.md` and `.scratch/litellm-proxy/ISSUE.md` for real examples of the `superseded` pattern.
