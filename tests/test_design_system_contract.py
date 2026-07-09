from __future__ import annotations

from pathlib import Path


DESIGN_DOC = Path("DESIGN.md")


def test_design_system_documents_theme_sources() -> None:
    text = DESIGN_DOC.read_text(encoding="utf-8")

    assert "packages/renderer/src/theme/themes" in text


def test_design_system_documents_accessibility_baseline() -> None:
    text = DESIGN_DOC.read_text(encoding="utf-8")

    for heading in ("Focus", "Contrast", "Reduced motion", "CJK and Vietnamese text"):
        assert heading in text


def test_design_system_documents_accepted_debt() -> None:
    text = DESIGN_DOC.read_text(encoding="utf-8")

    assert "Accepted debt" in text
