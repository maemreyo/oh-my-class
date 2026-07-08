import datetime
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))

from check_stale_scratch_issues import find_stale, months_ago, read_frontmatter  # noqa: E402


def test_months_ago_handles_year_rollover():
    assert months_ago(datetime.date(2026, 2, 1), 3) == datetime.date(2025, 11, 1)


def test_read_frontmatter_extracts_status_and_created(tmp_path):
    f = tmp_path / "issue.md"
    f.write_text('---\ntitle: "x"\nstatus: ready\ncreated: 2026-01-01\n---\nbody\n')
    fields = read_frontmatter(f)
    assert fields == {"status": "ready", "created": "2026-01-01"}


def test_find_stale_flags_old_ready_but_not_recent_or_done(tmp_path):
    old = tmp_path / "old.md"
    old.write_text("---\nstatus: ready\ncreated: 2025-01-01\n---\n")
    recent = tmp_path / "recent.md"
    recent.write_text("---\nstatus: ready\ncreated: 2026-07-01\n---\n")
    done = tmp_path / "done.md"
    done.write_text("---\nstatus: done\ncreated: 2025-01-01\n---\n")

    stale = find_stale(tmp_path, datetime.date(2026, 7, 8))

    assert [p.name for p, _, _ in stale] == ["old.md"]


if __name__ == "__main__":
    test_months_ago_handles_year_rollover()
    print("ok")
