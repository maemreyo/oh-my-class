"""Repair drifted ON DELETE rules on artifact_documents lineage FKs.

Revision ID: 037_fix_fk_ondelete_drift
Revises: 036_export_capability_version
Create Date: 2026-07-11

`030_artifact_document_lineage` has always declared `artifact_documents
.parent_document_id`/`.source_document_id` as `ON DELETE SET NULL`, and
`content_variants.source_document_id`/`content_dependencies
.source_document_id` as `ON DELETE CASCADE` (see that revision, unchanged
since it was written). But environments where `content_variants` or
`content_dependencies` were first materialized before those `ondelete`
arguments existed on the SQLAlchemy models (e.g. an ad-hoc
`Base.metadata.create_all()` in a test fixture racing the migration's
`if not inspector.has_table(...)` guard) ended up with the default `NO
ACTION` instead. That silently breaks run deletion/hard-erase: deleting a
run whose artifacts have a translation, variant, or dependency edge fails
with a foreign-key violation instead of cascading, which #451 (Language
Versions and typed Content Variants) surfaced by being the first code path
to ever populate `content_variants`/`content_dependencies` outside a test.

This migration re-asserts the originally-declared rule on each FK,
independent of what a given environment's constraint currently is --
running it twice is a no-op, and environments that were never drifted are
unaffected (`DROP CONSTRAINT IF EXISTS` + re-`ADD CONSTRAINT` either way).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "037_fix_fk_ondelete_drift"
down_revision: str | None = "036_export_capability_version"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (table, constraint_name, column, ondelete) -- ondelete matches each
# column's original declaration in 030_artifact_document_lineage.
_FK_REPAIRS: tuple[tuple[str, str, str, str], ...] = (
    ("artifact_documents", "artifact_documents_parent_document_id_fkey", "parent_document_id", "SET NULL"),
    ("artifact_documents", "artifact_documents_source_document_id_fkey", "source_document_id", "SET NULL"),
    ("content_variants", "content_variants_source_document_id_fkey", "source_document_id", "CASCADE"),
    ("content_dependencies", "content_dependencies_source_document_id_fkey", "source_document_id", "CASCADE"),
)


def upgrade() -> None:
    for table, constraint_name, column, ondelete in _FK_REPAIRS:
        op.execute(f'ALTER TABLE public."{table}" DROP CONSTRAINT IF EXISTS "{constraint_name}"')
        op.execute(
            f'ALTER TABLE public."{table}" '
            f'ADD CONSTRAINT "{constraint_name}" FOREIGN KEY ("{column}") '
            f'REFERENCES public.artifact_documents (document_id) ON DELETE {ondelete}',
        )


def downgrade() -> None:
    # The drifted state (NO ACTION) was never an intentional rule -- there is
    # nothing correct to roll back to, so downgrade is a no-op.
    pass
