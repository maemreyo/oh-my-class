"""AnkiApkgExporter — generates .apkg via genanki.

Usage:
    from packages.renderer.src.exporters.anki_apkg.index import export_apkg

    cards = [
        {"front": "Hello", "back": "Xin chào", "tags": ["english", "greeting"]},
        {"front": "Goodbye", "back": "Tạm biệt", "tags": ["english", "greeting"]},
    ]
    output_path = export_apkg("English Vocabulary", cards, "deck.apkg")

Dependencies:
    uv add genanki  (in packages/agents or root pyproject.toml)
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AnkiCard:
    front:  str
    back:   str
    tags:   list[str] = field(default_factory=list)


def _stable_id(name: str) -> int:
    """Generate a stable 32-bit deck/model ID from a name string."""
    return int(hashlib.md5(name.encode()).hexdigest()[:8], 16)


def export_apkg(
    deck_name: str,
    cards: list[AnkiCard] | list[dict[str, object]],
    output_path: str | Path,
) -> Path:
    """Export a list of cards as a .apkg file using genanki.

    Args:
        deck_name:   Name of the Anki deck (shown in Anki browser)
        cards:       List of AnkiCard or dicts with front/back/tags keys
        output_path: Path where the .apkg file will be written

    Returns:
        Resolved path of the created .apkg file

    Raises:
        ImportError: if genanki is not installed
    """
    try:
        import genanki  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ImportError(
            "genanki is required for Anki export. "
            "Install it with: uv add genanki"
        ) from exc

    model = genanki.Model(
        _stable_id(f"model:{deck_name}"),
        "oh-my-class Basic",
        fields=[{"name": "Front"}, {"name": "Back"}],
        templates=[
            {
                "name":  "Card 1",
                "qfmt":  "{{Front}}",
                "afmt":  "{{FrontSide}}<hr id=\"answer\">{{Back}}",
            }
        ],
    )

    deck = genanki.Deck(
        _stable_id(f"deck:{deck_name}"),
        deck_name,
    )

    for raw in cards:
        card = raw if isinstance(raw, AnkiCard) else AnkiCard(
            front=str(raw.get("front", "")),
            back=str(raw.get("back", "")),
            tags=[str(t) for t in raw.get("tags", [])],  # type: ignore[union-attr]
        )
        note = genanki.Note(
            model=model,
            fields=[card.front, card.back],
            tags=card.tags,
        )
        deck.add_note(note)

    package = genanki.Package(deck)
    out = Path(output_path).resolve()
    package.write_to_file(str(out))
    return out
