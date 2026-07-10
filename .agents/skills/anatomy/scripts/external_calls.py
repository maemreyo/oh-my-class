#!/usr/bin/env python3
"""
external_calls.py -- heuristic detection of cross-service/network
interactions, for Phase 3 of the anatomy skill's tracing workflow. This is
the companion to import_graph.py: that script only sees edges that go
through a same-language import/require/use statement, which makes it
structurally blind to how services actually talk to each other in most
real systems -- an HTTP call to another service, a gRPC stub invocation, a
message published to a queue and consumed somewhere else, a cron job, a
webhook registration. None of these involve importing the thing on the
other end, so import_graph.py has nothing to find. This script greps for
the common patterns of each instead.

Usage:
    python3 external_calls.py <repo_root> [--kinds http_client,grpc_client,queue,cron,webhook_route] [--modules modules.json]

Prints JSON to stdout: a flat list of hits, each with the file/line it was
found at, a kind, a framework/library guess, and whatever identifying
detail could be extracted (a URL, a topic/event name, a cron schedule). For
queue-related hits it also reports `possible_pairs`: publish/subscribe hits
that named the same topic or event string, which is the closest this script
can get to hypothesizing a same-process pub/sub edge without any import
connecting the two sides.

--modules <modules.json>: same flag and same reason as import_graph.py --
each hit's `top_level` field (and therefore `counts_by_top_level` and
`possible_pub_sub_pairs`' published_from/consumed_by) is grouped by actual
module boundary instead of the first path segment under repo root. Without
this, a project with a wrapping directory (src/, app/, lib/) reports every
hit under that one wrapper name, which is particularly unhelpful for
possible_pub_sub_pairs -- a publisher in one module and a consumer in
another both show up as "src", making a real cross-module pub/sub edge look
like a same-module no-op. Pass --modules once Phase 2's module boundaries
exist.

THIS IS A HYPOTHESIS GENERATOR, NOT GROUND TRUTH -- same caveat as
import_graph.py, and if anything a stronger one: covering every HTTP
client, gRPC framework, queue library, scheduler, and webhook convention in
use across languages isn't actually possible with regexes, so treat the
kind/framework list below as a representative starting set, not an
exhaustive one. A hit here means "worth opening this file and confirming
what it actually does" -- not "this edge is real," and the absence of a hit
does not mean a codebase has no external calls, just that this script
didn't recognize the pattern it used. Run it on every project, including
ones that look like a single monolith -- plenty of monoliths still call a
payment gateway, send a webhook, or run a forgotten cron job.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    walk_source_files, load_module_map, resolve_module_for_path,
)

ALL_KINDS = ["http_client", "grpc_client", "queue", "cron", "webhook_route"]

WEBHOOK_HINT = re.compile(r"webhook|callback|hook(?!s?\.)", re.IGNORECASE)


def top_level_of(rel_path: Path):
    parts = rel_path.parts
    return parts[0] if len(parts) > 1 else "(root)"


# ----------------------------------------------------------------------
# HTTP client calls (outgoing) -- (framework, regex, url_group)
# ----------------------------------------------------------------------
HTTP_CLIENT_PATTERNS = [
    ("python-requests", re.compile(r"\brequests\.(get|post|put|delete|patch|head)\(\s*f?['\"]([^'\"]+)"), 2),
    ("python-httpx", re.compile(r"\bhttpx\.(get|post|put|delete|patch)\(\s*f?['\"]([^'\"]+)"), 2),
    ("python-urllib", re.compile(r"urlopen\(\s*f?['\"]([^'\"]+)"), 1),
    ("js-axios", re.compile(r"\baxios\.(get|post|put|delete|patch)\(\s*['\"]([^'\"]+)"), 2),
    ("js-fetch", re.compile(r"\bfetch\(\s*['\"]([^'\"]+)"), 1),
    ("go-net-http", re.compile(r'http\.(Get|Post)\(\s*"([^"]+)"'), 2),
    ("java-resttemplate", re.compile(r"restTemplate\.\w+\(\s*\"([^\"]+)\""), 1),
    ("ruby-nethttp", re.compile(r"Net::HTTP\.get\(\s*[^)]*?['\"]([^'\"]+)"), 1),
    ("php-guzzle", re.compile(r"->request\(\s*['\"]\w+['\"]\s*,\s*['\"]([^'\"]+)"), 1),
    ("csharp-httpclient", re.compile(r"\.(?:GetAsync|PostAsync|PutAsync|DeleteAsync)\(\s*\"([^\"]+)\""), 1),
]

# ----------------------------------------------------------------------
# gRPC client stub creation
# ----------------------------------------------------------------------
GRPC_CLIENT_PATTERNS = [
    ("python-grpc", re.compile(r"(\w+(?:Service)?Stub)\(\s*\w*channel\w*\s*\)")),
    ("go-grpc", re.compile(r"pb\.New(\w+)Client\(")),
    ("java-grpc", re.compile(r"(\w+)Grpc\.new(?:Blocking|Future)?Stub\(")),
]

# ----------------------------------------------------------------------
# Queue publish / consume -- (framework, regex, kind, name_group)
# ----------------------------------------------------------------------
QUEUE_PATTERNS = [
    ("kafka-producer", re.compile(r"\b\w*[Pp]roducer\w*\.send\(\s*['\"]([^'\"]+)"), "publish"),
    ("kafka-consumer-topic", re.compile(r"KafkaConsumer\(\s*['\"]([^'\"]+)"), "consume"),
    ("generic-publish", re.compile(r"\.publish\(\s*['\"]([^'\"]+)"), "publish"),
    ("rabbitmq-publish", re.compile(r"basic_publish\([^)]*routing_key\s*=\s*['\"]([^'\"]+)"), "publish"),
    ("rabbitmq-consume", re.compile(r"basic_consume\("), "consume"),
    ("sqs-send", re.compile(r"\.send_message\("), "publish"),
    ("sns-publish", re.compile(r"\bsns\w*\.publish\("), "publish"),
    ("generic-emit", re.compile(r"\.emit\(\s*['\"]([^'\"]+)"), "publish"),
    ("generic-subscribe", re.compile(r"\.subscribe\(\s*['\"]([^'\"]+)"), "consume"),
    ("generic-consume", re.compile(r"\.consume\(\s*['\"]([^'\"]+)"), "consume"),
    ("generic-on-event", re.compile(r"\.on\(\s*['\"]([^'\"]+)"), "consume"),
]

# ----------------------------------------------------------------------
# Cron / scheduled jobs
# ----------------------------------------------------------------------
CRON_LINE_PATTERNS = [
    ("apscheduler", re.compile(r"\.add_job\(")),
    ("celery-beat", re.compile(r"(?:CELERYBEAT_SCHEDULE|beat_schedule)\s*=")),
    ("node-cron", re.compile(r"\bcron\.schedule\(\s*['\"]([^'\"]+)")),
    ("generic-decorator", re.compile(r"@(?:periodic_task|scheduled|cron)\b")),
]
CRONTAB_LINE = re.compile(
    r"^\s*(\S+\s+\S+\s+\S+\s+\S+\s+\S+)\s+(?!#)(\S.*)$"
)
K8S_CRONJOB_KIND = re.compile(r"^\s*kind:\s*CronJob\s*$")
K8S_SCHEDULE = re.compile(r"^\s*schedule:\s*['\"]?([^'\"\n]+?)['\"]?\s*$")

# ----------------------------------------------------------------------
# Webhook routes -- reuse a light route regex, keep only webhook-flavored hits
# ----------------------------------------------------------------------
ROUTE_PATTERNS = [
    ("flask", re.compile(r'@\w*\.route\(\s*[\'"]([^\'"]+)[\'"]')),
    ("fastapi", re.compile(r'@\w+\.(?:get|post|put|delete|patch)\(\s*[\'"]([^\'"]+)[\'"]')),
    ("express", re.compile(r'\b(?:app|router)\.(?:get|post|put|delete|patch|all)\(\s*[\'"]([^\'"]+)[\'"]')),
    ("rails", re.compile(r'^\s*(?:get|post|put|patch|delete)\s+[\'"]([^\'"]+)[\'"]')),
    ("spring", re.compile(r'@(?:Get|Post|Put|Delete|Patch|Request)Mapping\(\s*(?:value\s*=\s*)?[\'"]([^\'"]*)[\'"]')),
    ("laravel", re.compile(r'Route::(?:get|post|put|patch|delete)\(\s*[\'"]([^\'"]+)[\'"]')),
]


def scan_file(rel_path: Path, lines, kinds_wanted, hits, module_map=None):
    top = resolve_module_for_path(rel_path.parts, module_map) if module_map is not None else top_level_of(rel_path)
    if top is None:
        top = top_level_of(rel_path)  # unmapped file -- fall back rather than dropping the hit
    is_crontab_like = rel_path.name in {"crontab"} or rel_path.suffix == ".cron"
    is_yaml = rel_path.suffix.lower() in {".yaml", ".yml"}

    saw_cronjob_kind = False
    for i, line in enumerate(lines, start=1):

        if "http_client" in kinds_wanted:
            for framework, pat, url_group in HTTP_CLIENT_PATTERNS:
                m = pat.search(line)
                if m:
                    hits.append({
                        "file": str(rel_path), "line": i, "kind": "http_client",
                        "framework": framework, "detail": m.group(url_group),
                        "top_level": top,
                    })

        if "grpc_client" in kinds_wanted:
            for framework, pat in GRPC_CLIENT_PATTERNS:
                m = pat.search(line)
                if m:
                    hits.append({
                        "file": str(rel_path), "line": i, "kind": "grpc_client",
                        "framework": framework, "detail": "stub: " + m.group(1),
                        "top_level": top,
                    })

        if "queue" in kinds_wanted:
            for framework, pat, direction in QUEUE_PATTERNS:
                m = pat.search(line)
                if m:
                    name = m.group(1) if m.groups() else None
                    hits.append({
                        "file": str(rel_path), "line": i,
                        "kind": "queue_" + direction, "framework": framework,
                        "detail": name, "top_level": top,
                    })

        if "cron" in kinds_wanted:
            for framework, pat in CRON_LINE_PATTERNS:
                m = pat.search(line)
                if m:
                    detail = m.group(1) if m.groups() else line.strip()[:80]
                    hits.append({
                        "file": str(rel_path), "line": i, "kind": "cron",
                        "framework": framework, "detail": detail, "top_level": top,
                    })
            if is_crontab_like:
                m = CRONTAB_LINE.match(line)
                if m:
                    hits.append({
                        "file": str(rel_path), "line": i, "kind": "cron",
                        "framework": "crontab", "detail": line.strip(), "top_level": top,
                    })
            if is_yaml:
                if K8S_CRONJOB_KIND.match(line):
                    saw_cronjob_kind = True
                elif saw_cronjob_kind:
                    m = K8S_SCHEDULE.match(line)
                    if m:
                        hits.append({
                            "file": str(rel_path), "line": i, "kind": "cron",
                            "framework": "k8s-cronjob", "detail": m.group(1).strip(),
                            "top_level": top,
                        })
                        saw_cronjob_kind = False

        if "webhook_route" in kinds_wanted:
            for framework, pat in ROUTE_PATTERNS:
                m = pat.search(line)
                if m and WEBHOOK_HINT.search(m.group(1)):
                    hits.append({
                        "file": str(rel_path), "line": i, "kind": "webhook_route",
                        "framework": framework, "detail": m.group(1), "top_level": top,
                    })


def find_pub_sub_pairs(hits):
    """Group queue_publish/queue_consume hits by matching topic/event name --
    a hint at a same-process pub/sub edge that has no import connecting the
    two sides. Best-effort string match only; doesn't account for templated
    topic names, prefixes, or environment-specific naming."""
    publishers, consumers = {}, {}
    for h in hits:
        if not h.get("detail"):
            continue
        if h["kind"] == "queue_publish":
            publishers.setdefault(h["detail"], []).append(h)
        elif h["kind"] == "queue_consume":
            consumers.setdefault(h["detail"], []).append(h)
    pairs = []
    for name in sorted(set(publishers) & set(consumers)):
        pairs.append({
            "topic_or_event": name,
            "published_from": sorted({h["top_level"] for h in publishers[name]}),
            "consumed_by": sorted({h["top_level"] for h in consumers[name]}),
        })
    return pairs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo_root")
    ap.add_argument("--kinds", default=",".join(ALL_KINDS),
                     help="comma-separated subset of: " + ",".join(ALL_KINDS))
    ap.add_argument(
        "--modules", default=None,
        help="path to Phase 2's modules.json (slug -> relative-path); when "
             "given, each hit's top_level field is the actual owning module "
             "instead of a guess from the first path segment",
    )
    args = ap.parse_args()

    kinds_wanted = set(k.strip() for k in args.kinds.split(",") if k.strip())
    repo_root = Path(args.repo_root).resolve()
    module_map = load_module_map(args.modules)

    hits = []
    for abs_path, rel_path in walk_source_files(repo_root):
        try:
            text = abs_path.read_text(errors="ignore")
        except OSError:
            continue
        if not text:
            continue
        lines = text.splitlines()
        scan_file(rel_path, lines, kinds_wanted, hits, module_map=module_map)

    counts_by_kind = {}
    counts_by_top_level = {}
    for h in hits:
        counts_by_kind[h["kind"]] = counts_by_kind.get(h["kind"], 0) + 1
        counts_by_top_level[h["top_level"]] = counts_by_top_level.get(h["top_level"], 0) + 1

    result = {
        "repo_root": str(repo_root),
        "hits": hits,
        "counts_by_kind": counts_by_kind,
        "counts_by_top_level": counts_by_top_level,
        "possible_pub_sub_pairs": find_pub_sub_pairs(hits),
        "note": (
            "Hypothesis generator, not ground truth -- see this script's "
            "module docstring. Every hit needs its call site opened and "
            "confirmed before it goes into a module doc or diagram."
        ) + (
            " top_level fields are grouped by --modules' module boundaries."
            if module_map is not None else
            " top_level fields are grouped by first path segment under repo "
            "root -- pass --modules <modules.json> for accurate grouping on "
            "a project with a wrapping directory (src/, app/, lib/)."
        ),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()