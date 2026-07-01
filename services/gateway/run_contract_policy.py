from __future__ import annotations

from hashlib import sha256
from json import dumps
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.gateway.teaching_pack_types import JsonObject

SUPPORTED_ARTIFACTS = {"lesson", "worksheet", "quiz", "drill", "recap", "infographic"}
SUPPORTED_EXPORTS = {"html", "gift", "h5p", "qti", "anki_apkg", "flashcard_tsv", "google_forms"}
CONFIG_VERSION = "teaching-packs-contract-setup@1"
DEFAULT_POLICY = {
    "artifact_types": ["lesson", "worksheet", "quiz"],
    "export_formats": ["html"],
    "research_policy": "standard",
    "locale": "en-US",
    "instruction_language": "en",
}


def config_hash(policy: JsonObject) -> str:
    encoded = dumps(policy, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()
