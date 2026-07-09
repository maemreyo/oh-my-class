# Triage Labels

The skills speak in terms of five canonical triage roles. This file maps those roles to the actual label strings used in this repo's issue tracker.

| Label in mattpocock/skills | Label in our tracker | Meaning                                  |
| -------------------------- | -------------------- | ---------------------------------------- |
| `needs-triage`             | _(not used)_         | Maintainer needs to evaluate this issue  |
| `needs-info`               | `needs-info`         | Waiting on reporter for more information |
| `ready-for-agent`          | `ready-for-agent`    | Fully specified, ready for an AFK agent  |
| `ready-for-human`          | _(not used)_         | Requires human implementation            |
| `wontfix`                  | _(not used)_         | Will not be actioned                     |
| `done`                     | `done`               | Completed and closed                     |

**Active labels**: `needs-info`, `ready-for-agent`, `done`.

## State machine

```
open (needs-info) → open (ready-for-agent) → closed (done)
```

When a skill mentions a role (e.g. "apply the AFK-ready triage label"), use the corresponding label string from this table. Skip any skill action that references an unused label.
