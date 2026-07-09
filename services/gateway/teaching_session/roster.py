"""CSV roster import scoped to `class_id` (TSP-02 amendment #4).

Lets `identifiable`-tier sessions (TSP-01) offer a name-select dropdown at
join instead of free-text name entry. No external SIS integration in this
slice -- rows only ever come from a teacher-uploaded CSV, and a roster entry
never creates a `users` row.
"""

from __future__ import annotations

import csv
from io import StringIO
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import delete, select

from services.gateway.teaching_session.models import ClassRosterEntry

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class RosterImportError(ValueError):
    """Raised for a structurally invalid roster CSV (e.g. no `name` column)."""


def parse_roster_csv(csv_text: str) -> list[tuple[str, str | None]]:
    """Parse `name[,student_id]` rows. `name` column is required; blank names skipped."""
    reader = csv.DictReader(StringIO(csv_text.strip()))
    if reader.fieldnames is None or "name" not in reader.fieldnames:
        raise RosterImportError("Roster CSV must have a 'name' column")

    rows: list[tuple[str, str | None]] = []
    for row in reader:
        name = (row.get("name") or "").strip()
        if not name:
            continue
        student_id = (row.get("student_id") or "").strip() or None
        rows.append((name, student_id))
    return rows


async def import_roster(
    db: AsyncSession,
    *,
    class_id: str,
    csv_text: str,
    imported_by: str,
) -> list[ClassRosterEntry]:
    """Replace `class_id`'s roster with the rows in `csv_text`.

    A re-import fully replaces the prior roster for this class -- the CSV is
    treated as the authoritative current class list, not an incremental
    patch. Caller is expected to `await db.commit()` (matches
    `teaching_session.service.create_session`'s add-and-flush convention).
    """
    rows = parse_roster_csv(csv_text)

    await db.execute(delete(ClassRosterEntry).where(ClassRosterEntry.class_id == class_id))

    entries = [
        ClassRosterEntry(
            roster_entry_id=f"roster-{uuid4()}",
            class_id=class_id,
            name=name,
            student_id=student_id,
            imported_by=imported_by,
        )
        for name, student_id in rows
    ]
    db.add_all(entries)
    await db.flush()
    return entries


async def list_roster(db: AsyncSession, *, class_id: str) -> list[ClassRosterEntry]:
    """Roster entries for a class, for the join-time name-select dropdown."""
    result = await db.execute(
        select(ClassRosterEntry)
        .where(ClassRosterEntry.class_id == class_id)
        .order_by(ClassRosterEntry.name),
    )
    return list(result.scalars().all())


async def get_roster_entry(
    db: AsyncSession, *, class_id: str, roster_entry_id: str,
) -> ClassRosterEntry | None:
    """Look up one roster entry, scoped to `class_id`.

    This is what makes a roster join "authenticated" rather than free-text
    pseudonymous (base AC1): `teaching_session.join.join_session` requires a
    `ClassRosterEntry` object here, not a client-supplied name/ID string, so
    a student can only claim an identity that a teacher's CSV import actually
    put in this class's roster.
    """
    result = await db.execute(
        select(ClassRosterEntry).where(
            ClassRosterEntry.class_id == class_id,
            ClassRosterEntry.roster_entry_id == roster_entry_id,
        ),
    )
    return result.scalar_one_or_none()
