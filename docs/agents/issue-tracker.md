# Issue Tracker

Issues live as markdown files under `.scratch/<feature>/` in this repo.

## Structure

```
.scratch/
  <feature-slug>/
    ISSUE.md          # The issue body
    research/         # Optional: research notes
    artifacts/        # Optional: generated artifacts
```

## ISSUE.md Format

```yaml
---
title: Short description
status: needs-info | ready-for-agent
labels: []
created: YYYY-MM-DD
---
```

## Workflow

1. Create `.scratch/<feature>/ISSUE.md` with frontmatter
2. Triage skill updates `status` field
3. Agent skills read from this directory
