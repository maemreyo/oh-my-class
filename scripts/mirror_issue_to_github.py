"""Mirror a single `.scratch/<epic>/issues/*.md` issue file to a real GitHub issue.

Just-in-time mirroring only (per ADR-047 / Q28 design-interview decision): this
script mirrors ONE issue, called at the moment work on it actually starts — it
never bulk-mirrors a whole `ready-for-agent` backlog. Idempotent: re-running on
an already-mirrored file finds the existing GitHub issue (matched by a hidden
marker in the issue body) and does nothing.

Usage:
    python scripts/mirror_issue_to_github.py .scratch/slide-deck-editor/issues/SDE-01-content-materialization-llm-integration.md
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

_FRONTMATTER_RE: Final = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
_MARKER_PREFIX: Final = "<!-- mirrored-from:"


@dataclass(frozen=True, slots=True)
class IssueFile:
    path: Path
    title: str
    labels: tuple[str, ...]
    body: str

    @property
    def marker(self) -> str:
        return f"{_MARKER_PREFIX}{self.path.as_posix()} -->"


def parse_issue_file(path: Path) -> IssueFile:
    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    if not match:
        msg = f"{path}: missing frontmatter block (expected '---\\n...\\n---\\n')"
        raise ValueError(msg)

    frontmatter, body = match.groups()
    fields: dict[str, str] = {}
    for line in frontmatter.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()

    title = fields.get("title", path.stem)
    labels_raw = frontmatter[frontmatter.find("labels:") :].splitlines()[0]
    labels_match = re.search(r"\[(.*?)\]", labels_raw)
    labels = (
        tuple(label.strip() for label in labels_match.group(1).split(","))
        if labels_match
        else ()
    )
    return IssueFile(path=path, title=title, labels=labels, body=body.strip())


def find_existing_issue(issue: IssueFile) -> str | None:
    """Return the existing GitHub issue URL if this file was already mirrored."""
    result = subprocess.run(
        ["gh", "issue", "list", "--state", "all", "--search", issue.marker, "--json", "url"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        if '"url"' in line:
            url_match = re.search(r'"url":\s*"([^"]+)"', line)
            if url_match:
                return url_match.group(1)
    return None


def create_github_issue(issue: IssueFile) -> str:
    body_with_marker = f"{issue.body}\n\n{issue.marker}"
    args = ["gh", "issue", "create", "--title", issue.title, "--body", body_with_marker]
    for label in issue.labels:
        args.extend(["--label", label])
    result = subprocess.run(args, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 1

    path = Path(argv[1])
    if not path.is_file():
        print(f"error: {path} is not a file", file=sys.stderr)
        return 1

    issue = parse_issue_file(path)

    existing_url = find_existing_issue(issue)
    if existing_url:
        print(f"already mirrored: {existing_url}")
        return 0

    url = create_github_issue(issue)
    print(f"created: {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
