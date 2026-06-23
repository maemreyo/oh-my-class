# Triage Labels

| Label | Meaning |
|-------|---------|
| `needs-info` | Waiting on reporter for more details |
| `ready-for-agent` | Fully specified, AFK-ready |

## State Machine

```
needs-info → ready-for-agent (when info provided)
ready-for-agent → (agent picks up)
```
