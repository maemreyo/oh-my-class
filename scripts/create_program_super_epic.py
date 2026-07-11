#!/usr/bin/env python3
"""Create or refresh the Oh My Class Program Super Epic dispatcher.

The script reads all repository issues through an authenticated GitHub CLI,
discovers generated Epic/child markers, parses each child's ``Blocked by``
section, computes the live dependency frontier, and writes one concise Program
issue. It never mutates tracked Epics or child issues.

Requirements: Python 3.9+ and an authenticated ``gh`` with Issues read/write.

Examples:
  python scripts/create_program_super_epic.py --dry-run
  python scripts/create_program_super_epic.py --yes
  python scripts/create_program_super_epic.py --yes --top 20

Reruns are idempotent through a stable HTML marker. Use this Program issue as
the single entry point for coding agents; the linked child issues remain the
canonical implementation scope and acceptance criteria.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable


PROGRAM_KEY = "oh-my-class-program-control-plane-v1"
DEFAULT_REPO = "maemreyo/oh-my-class"
SUPER_EPIC_TITLE = "Program: Build and Certify the Oh My Class Teaching Content Platform"
REQUEST_TIMEOUT_SECONDS = 90

MARKER_RE = re.compile(
    r"<!--\s*omc-program:(?P<program>[a-z0-9-]+);\s*issue:(?P<key>[a-z0-9_-]+)\s*-->"
)
BLOCKED_SECTION_RE = re.compile(
    r"(?ms)^## Blocked by\s*\n+(?P<body>.*?)(?=^##\s|\Z)"
)
ISSUE_NUMBER_RE = re.compile(r"#(?P<number>\d+)")


@dataclass(frozen=True)
class ProgramSpec:
    key: str
    label: str
    priority: int
    role: str
    terminal_issue: int


PROGRAMS: tuple[ProgramSpec, ...] = (
    ProgramSpec(
        key="teaching-content-factory-v2",
        label="Teaching Content Factory V2",
        priority=0,
        role="Architecture, taxonomy, V2 authority, orchestration, Content Intelligence, quality and durable runtime foundation.",
        terminal_issue=474,
    ),
    ProgramSpec(
        key="creator-trust-plane-v1",
        label="Creator Workspace and Content Trust Plane",
        priority=1,
        role="Contracts, model policy, source/rights safety, knowledge releases, product workspace and evaluation lab.",
        terminal_issue=487,
    ),
    ProgramSpec(
        key="pedagogical-intelligence-kernel-v1",
        label="Pedagogical Intelligence Compiler",
        priority=2,
        role="TeachingIntent, objective graph, Program/Semantic IR, optimization, synthesis, tools and core intelligence certification.",
        terminal_issue=503,
    ),
    ProgramSpec(
        key="methodology-operating-system-v1",
        label="Evidence-Grounded Methodology OS",
        priority=3,
        role="Executable signed pedagogy packs, applicability, selection/composition, fidelity, projections and methodology certification.",
        terminal_issue=538,
    ),
    ProgramSpec(
        key="export-delivery-hardening-v1",
        label="Lossless Export Delivery Plane",
        priority=3,
        role="Immutable export receipts/blobs, Projection Kernel cutover, format conformance, delivery and multi-replica certification.",
        terminal_issue=521,
    ),
)

PROGRAM_BY_KEY = {program.key: program for program in PROGRAMS}

# Cross-Epic convergence gates may not yet be mirrored into the older issue
# bodies. They are explicit Program policy, unioned with each issue's textual
# ``Blocked by`` section so the dispatcher cannot recommend certification too
# early. This does not mutate the referenced issues.
PROGRAM_GATES: dict[int, tuple[int, ...]] = {
    503: (538,),
    474: (487, 503, 521),
}


@dataclass(frozen=True)
class IssueRecord:
    number: int
    title: str
    state: str
    body: str
    html_url: str
    labels: tuple[str, ...]
    program_key: str | None
    issue_key: str | None
    blockers: tuple[int, ...]

    @property
    def is_open(self) -> bool:
        return self.state.casefold() == "open"

    @property
    def is_epic(self) -> bool:
        return self.issue_key == "epic"


def progress(message: str) -> None:
    print(message, flush=True)


def run_gh(arguments: list[str], *, input_data: dict[str, Any] | None = None) -> Any:
    command = ["gh", *arguments]
    try:
        completed = subprocess.run(
            command,
            input=json.dumps(input_data) if input_data is not None else None,
            text=True,
            capture_output=True,
            check=False,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"GitHub CLI timed out after {REQUEST_TIMEOUT_SECONDS}s: {' '.join(command)}"
        ) from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(
            f"Command failed ({completed.returncode}): {' '.join(command)}\n{detail}"
        )
    output = completed.stdout.strip()
    return json.loads(output) if output else None


def check_gh_auth() -> None:
    completed = subprocess.run(
        ["gh", "auth", "status"],
        text=True,
        capture_output=True,
        check=False,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"GitHub CLI is not authenticated:\n{detail}")


def super_marker() -> str:
    return f"<!-- omc-program:{PROGRAM_KEY}; issue:epic -->"


def parse_marker(body: str) -> tuple[str | None, str | None]:
    match = MARKER_RE.search(body)
    if match is None:
        return None, None
    return match.group("program"), match.group("key")


def parse_blockers(body: str) -> tuple[int, ...]:
    match = BLOCKED_SECTION_RE.search(body)
    if match is None:
        return ()
    section = match.group("body")
    return tuple(dict.fromkeys(int(item.group("number")) for item in ISSUE_NUMBER_RE.finditer(section)))


def load_all_issues(repo: str) -> list[IssueRecord]:
    pages = run_gh([
        "api", "--paginate", "--slurp",
        f"repos/{repo}/issues?state=all&per_page=100",
    ])
    if not isinstance(pages, list):
        raise RuntimeError("Unexpected GitHub issues response: expected paginated list")
    rows: list[dict[str, Any]] = []
    for page in pages:
        if isinstance(page, list):
            rows.extend(item for item in page if isinstance(item, dict))
    records: list[IssueRecord] = []
    for row in rows:
        if "pull_request" in row:
            continue
        body = str(row.get("body") or "")
        program_key, issue_key = parse_marker(body)
        labels = tuple(
            str(label.get("name"))
            for label in row.get("labels", [])
            if isinstance(label, dict) and label.get("name")
        )
        records.append(IssueRecord(
            number=int(row["number"]),
            title=str(row.get("title") or ""),
            state=str(row.get("state") or "unknown"),
            body=body,
            html_url=str(row.get("html_url") or ""),
            labels=labels,
            program_key=program_key,
            issue_key=issue_key,
            blockers=parse_blockers(body),
        ))
    return records


def readiness(issue: IssueRecord, issue_by_number: dict[int, IssueRecord]) -> tuple[bool, tuple[int, ...], tuple[int, ...]]:
    open_blockers: list[int] = []
    unknown_blockers: list[int] = []
    for number in effective_blockers(issue):
        blocker = issue_by_number.get(number)
        if blocker is None:
            unknown_blockers.append(number)
        elif blocker.is_open:
            open_blockers.append(number)
    ready = issue.is_open and not open_blockers and not unknown_blockers
    return ready, tuple(open_blockers), tuple(unknown_blockers)


def effective_blockers(issue: IssueRecord) -> tuple[int, ...]:
    return tuple(dict.fromkeys((*issue.blockers, *PROGRAM_GATES.get(issue.number, ()))))


def tracked_children(issues: Iterable[IssueRecord]) -> list[IssueRecord]:
    return [
        issue for issue in issues
        if issue.program_key in PROGRAM_BY_KEY and not issue.is_epic
    ]


def tracked_epics(issues: Iterable[IssueRecord]) -> dict[str, IssueRecord]:
    return {
        issue.program_key: issue
        for issue in issues
        if issue.program_key in PROGRAM_BY_KEY and issue.is_epic
    }


def dependent_counts(children: Iterable[IssueRecord]) -> dict[int, int]:
    counts: dict[int, int] = {}
    for child in children:
        if not child.is_open:
            continue
        for blocker in effective_blockers(child):
            counts[blocker] = counts.get(blocker, 0) + 1
    return counts


def is_certification(issue: IssueRecord, program: ProgramSpec) -> bool:
    lowered = issue.title.casefold()
    return issue.number == program.terminal_issue or "certif" in lowered or "cut over" in lowered


def ready_frontier(
    children: list[IssueRecord], issue_by_number: dict[int, IssueRecord]
) -> list[IssueRecord]:
    counts = dependent_counts(children)
    ready = [issue for issue in children if readiness(issue, issue_by_number)[0]]
    return sorted(
        ready,
        key=lambda issue: (
            PROGRAM_BY_KEY[issue.program_key or ""].priority,
            is_certification(issue, PROGRAM_BY_KEY[issue.program_key or ""]),
            -counts.get(issue.number, 0),
            issue.number,
        ),
    )


def state_icon(state: str) -> str:
    return "✅" if state.casefold() == "closed" else "🟢" if state.casefold() == "open" else "❔"


def render_program_body(issues: list[IssueRecord], *, top: int) -> str:
    issue_by_number = {issue.number: issue for issue in issues}
    children = tracked_children(issues)
    epics = tracked_epics(issues)
    frontier = ready_frontier(children, issue_by_number)
    counts = dependent_counts(children)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    lines = [
        super_marker(),
        "## Mission",
        "Build and certify a modern, trustworthy, pedagogically powerful teaching-content platform. This Program issue is the AI work dispatcher; linked Epic and child bodies remain the canonical implementation scope.",
        "## Live program status",
        f"Generated from repository issue state at `{generated_at}` by `create_program_super_epic.py`.",
    ]
    table_lines = [
        "| Epic | Role | Open | Ready now | Blocked | Closed | Terminal gate |",
        "|---|---|---:|---:|---:|---:|---|",
    ]

    for program in PROGRAMS:
        epic = epics.get(program.key)
        program_children = [child for child in children if child.program_key == program.key]
        open_children = [child for child in program_children if child.is_open]
        ready_children = [child for child in open_children if readiness(child, issue_by_number)[0]]
        blocked_children = [child for child in open_children if not readiness(child, issue_by_number)[0]]
        closed_children = [child for child in program_children if not child.is_open]
        epic_cell = (
            f"{state_icon(epic.state)} #{epic.number} {program.label}"
            if epic is not None else f"❔ {program.label} — Epic marker not found"
        )
        terminal = issue_by_number.get(program.terminal_issue)
        terminal_cell = (
            f"{state_icon(terminal.state)} #{terminal.number}"
            if terminal is not None else f"❔ #{program.terminal_issue}"
        )
        table_lines.append(
            f"| {epic_cell} | {program.role} | {len(open_children)} | {len(ready_children)} | "
            f"{len(blocked_children)} | {len(closed_children)} | {terminal_cell} |"
        )

    lines.append("\n".join(table_lines))
    lines.extend([
        "## Current dependency frontier",
        "These are open tracked child issues whose complete textual `Blocked by` set is closed. Unknown blocker state is fail-closed and never appears here.",
    ])
    if frontier:
        for rank, issue in enumerate(frontier[:top], start=1):
            program = PROGRAM_BY_KEY[issue.program_key or ""]
            unlocks = counts.get(issue.number, 0)
            suffix = f"; directly unblocks {unlocks} tracked open issue(s)" if unlocks else ""
            lines.append(f"{rank}. **#{issue.number} — {issue.title}** — {program.label}{suffix}.")
    else:
        lines.append("No ready tracked child issue was found. Inspect unknown/missing blockers and sync the child Epic scripts before proceeding.")

    lines.extend([
        "## Recommended next action",
        (
            f"Start with **#{frontier[0].number} — {frontier[0].title}**. It is the highest-priority ready issue under the deterministic selection policy below."
            if frontier else "Repair the dependency metadata or close an outstanding blocker; do not guess readiness."
        ),
        "## Program dependency model",
        "```text\n#460 foundation frontier\n ├──> #475 trust/product foundations\n ├──> #488 core intelligence ──> #522 Methodology OS ──> #503\n └──> #504 Export Delivery Plane ─────────────────────> #521\n\n#487 + #503 + #521 ──> #474 final V2 certification/cutover\n```",
        "The Epics are a DAG, not five monolithic sequential projects. Start work whenever the exact child blockers are closed; do not wait for an unrelated Epic branch to finish.",
        "## Deterministic agent selection policy",
        "1. Refresh this Program issue by running `python scripts/create_program_super_epic.py --yes`.",
        "2. Read this Program issue, then read the full body of the first issue in **Current dependency frontier**.",
        "3. Recheck every `Blocked by` issue live. Unknown, missing or open means blocked.",
        "4. Prefer lower program priority first: #460 foundation, #475 trust/runtime, #488 intelligence, then parallel Methodology/#504 lanes.",
        "5. Within a program priority, prefer non-certification work and the issue that directly unblocks the most tracked open issues; break ties by issue number.",
        "6. Implement exactly one child issue per PR unless its body explicitly defines an inseparable migration/cutover unit.",
        "7. Do not implement an open blocker inside a dependent issue and do not silently broaden authority or product scope.",
        "8. Completion requires the issue's real-path tests/evidence and Definition of Done; mocks, schemas, prompts, generated files and green status alone are insufficient.",
        "9. After merge/closure, refresh this Program issue and select again from the new frontier.",
        "## Copy-paste prompt for an AI coding agent",
        "> Read the Program issue and refresh its live dependency frontier. Select the highest-ranked ready child issue, revalidate all blockers, implement only that issue through the real production path, run its required tests, attach evidence, and open one focused PR. Do not bypass blockers or treat mocks/schema-only work as completion.",
        "## Certification convergence",
        "- Program policy treats Methodology OS certification #538 as a blocker of Core Intelligence certification #503 even before native/body metadata is mirrored.",
        "- Export Delivery certification #521 remains an independent terminal lane.",
        "- Program policy treats Creator/Trust #487, Core Intelligence #503 and Export Delivery #521 as blockers of #474.",
        "- Close this Program only after #474 is closed with signed real-path evidence and every tracked Epic is closed.",
        "## Maintenance policy",
        "- Do not hand-edit generated status/frontier sections; rerun the script.",
        "- Child issue bodies own blockers, tests and acceptance criteria. This issue only indexes and dispatches.",
        "- New generated Epics must receive a stable `omc-program` marker and be added to `PROGRAMS` with an explicit priority and terminal gate.",
        "- This script intentionally does not mutate native GitHub sub-issue/dependency relationships.",
    ])
    return "\n\n".join(lines).rstrip() + "\n"


def find_super_epic(issues: Iterable[IssueRecord]) -> IssueRecord | None:
    return next(
        (
            issue for issue in issues
            if issue.program_key == PROGRAM_KEY and issue.issue_key == "epic"
        ),
        None,
    )


def available_labels(repo: str) -> set[str]:
    rows = run_gh(["label", "list", "--repo", repo, "--limit", "500", "--json", "name"])
    return {str(row["name"]) for row in rows}


def create_issue(repo: str, body: str, labels: list[str]) -> dict[str, Any]:
    payload: dict[str, Any] = {"title": SUPER_EPIC_TITLE, "body": body}
    if labels:
        payload["labels"] = labels
    return run_gh(
        ["api", "--method", "POST", f"repos/{repo}/issues", "--input", "-"],
        input_data=payload,
    )


def update_issue(repo: str, number: int, body: str, labels: list[str]) -> dict[str, Any]:
    return run_gh(
        ["api", "--method", "PATCH", f"repos/{repo}/issues/{number}", "--input", "-"],
        input_data={"title": SUPER_EPIC_TITLE, "body": body, "labels": labels},
    )


def validate_configuration() -> None:
    keys = [program.key for program in PROGRAMS]
    priorities = [program.priority for program in PROGRAMS]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate ProgramSpec key")
    if any(not key or key == PROGRAM_KEY for key in keys):
        raise ValueError("Invalid tracked program key")
    if any(priority < 0 for priority in priorities):
        raise ValueError("Program priority must be non-negative")
    if len({program.terminal_issue for program in PROGRAMS}) != len(PROGRAMS):
        raise ValueError("Each ProgramSpec needs a distinct terminal issue")
    known_terminal_numbers = {program.terminal_issue for program in PROGRAMS}
    if not set(PROGRAM_GATES).issubset(known_terminal_numbers):
        raise ValueError("Program gates may target only tracked terminal issues")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=DEFAULT_REPO, help="GitHub repository in owner/name form")
    parser.add_argument("--yes", action="store_true", help="Create or update the Program issue")
    parser.add_argument("--dry-run", action="store_true", help="Render live body without mutation")
    parser.add_argument("--top", type=int, default=15, choices=range(1, 51), metavar="1..50", help="Number of ready frontier issues to display")
    parser.add_argument("--timeout", type=int, default=90, metavar="SECONDS", help="Timeout per gh operation")
    return parser.parse_args()


def main() -> int:
    global REQUEST_TIMEOUT_SECONDS
    args = parse_args()
    REQUEST_TIMEOUT_SECONDS = args.timeout
    validate_configuration()
    if shutil.which("gh") is None:
        raise RuntimeError("GitHub CLI gh was not found on PATH")

    progress("[1/4] Checking gh authentication...")
    check_gh_auth()
    progress(f"[2/4] Loading all repository issues from {args.repo}...")
    issues = load_all_issues(args.repo)
    body = render_program_body(issues, top=args.top)
    if len(body.encode()) >= 65536:
        raise RuntimeError(f"Rendered Program body exceeds GitHub limit: {len(body.encode())} bytes")

    if args.dry_run or not args.yes:
        print(body)
        print("No changes made. Use --yes to create or refresh the Program issue.")
        return 0

    progress("[3/4] Checking repository labels...")
    # Note: `gh repo view --json viewerPermission` does not return viewerPermission
    # when using GITHUB_TOKEN in GitHub Actions.  We rely on the subsequent gh api
    # calls to surface 403 errors if the token lacks write access.
    labels_present = available_labels(args.repo)
    labels = [name for name in ("epic", "feature", "architecture", "ready-for-agent") if name in labels_present]

    progress("[4/4] Creating or refreshing the Program dispatcher...")
    existing = find_super_epic(issues)
    if existing is None:
        created = create_issue(args.repo, body, labels)
        print(f"Created Program issue #{created['number']}: {created['html_url']}")
    else:
        updated = update_issue(args.repo, existing.number, body, labels)
        print(f"Updated Program issue #{existing.number}: {updated['html_url']}")

    children = tracked_children(issues)
    frontier = ready_frontier(children, {issue.number: issue for issue in issues})
    if frontier:
        print(f"Recommended next issue: #{frontier[0].number} — {frontier[0].title}")
    else:
        print("No ready tracked issue found; inspect unknown/open blockers.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
