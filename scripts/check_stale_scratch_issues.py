#!/usr/bin/env python3
"""Report .scratch/**/*.md issues that look stale.

Informational only: prints files with status in {ready, ready-for-agent,
deferred} whose `created` date is more than 3 months old. Never fails (exit 0
always) — staleness is a signal for human triage, not an automatic verdict.

See .scratch/README.md for the status/created frontmatter convention.
"""
import datetime
import pathlib
import re

STALE_STATUSES = {"ready", "ready-for-agent", "deferred"}
SCRATCH_DIR = pathlib.Path(__file__).resolve().parent.parent / ".scratch"

# ponytail: hand-rolled frontmatter reader instead of a yaml dep — these
# files are a flat `---\nkey: value\n---` block, no nesting. Upgrade to
# real yaml.safe_load if frontmatter ever grows lists/nested keys.
FIELD_RE = re.compile(r"^(status|created):\s*\"?([^\"\n]+?)\"?\s*$")


def read_frontmatter(path: pathlib.Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    with path.open(encoding="utf-8") as f:
        first = f.readline()
        if first.strip() != "---":
            return fields
        for line in f:
            if line.strip() == "---":
                break
            m = FIELD_RE.match(line.rstrip("\n"))
            if m:
                fields[m.group(1)] = m.group(2)
    return fields


def months_ago(today: datetime.date, months: int) -> datetime.date:
    year = today.year
    month = today.month - months
    while month <= 0:
        month += 12
        year -= 1
    day = min(today.day, 28)  # avoid day-out-of-range on short months
    return datetime.date(year, month, day)


StaleEntry = tuple[pathlib.Path, str, str]


def find_stale(scratch_dir: pathlib.Path, today: datetime.date) -> list[StaleEntry]:
    cutoff = months_ago(today, 3)
    stale = []
    for path in sorted(scratch_dir.rglob("*.md")):
        fields = read_frontmatter(path)
        status = fields.get("status")
        created = fields.get("created")
        if status not in STALE_STATUSES or not created:
            continue
        try:
            created_date = datetime.date.fromisoformat(created)
        except ValueError:
            continue
        if created_date < cutoff:
            stale.append((path, status, created))
    return stale


def main() -> None:
    today = datetime.date.today()
    stale = find_stale(SCRATCH_DIR, today)
    if not stale:
        print("No stale .scratch issues found.")
        return
    print(f"{len(stale)} stale .scratch issue(s) (ready/ready-for-agent/deferred, >3mo old):")
    for path, status, created in stale:
        print(f"  {path.relative_to(SCRATCH_DIR.parent)}\tstatus={status}\tcreated={created}")


if __name__ == "__main__":
    main()
