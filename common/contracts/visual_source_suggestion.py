"""Teacher-handled Visual Source Suggestions (ADR-056).

Research output describing a candidate visual is never an artifact asset by
itself -- a teacher must review its license, then upload the actual bytes
through the Media Library (`MediaAssetVersion`) before anything can
reference it. `candidate_url` here is informational only; nothing in the
system ever fetches or embeds it.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

VisualSourceSuggestionStatus = Literal["pending", "converted", "dismissed"]


class VisualSourceSuggestion(BaseModel):
    model_config = ConfigDict(frozen=True)

    suggestion_id: str = Field(min_length=1, max_length=80)
    run_id: str = Field(min_length=1, max_length=64)
    description: str = Field(min_length=1, max_length=1_000)
    candidate_url: str | None = Field(default=None, max_length=2_000)
    license_hint: str | None = Field(default=None, max_length=500)
    status: VisualSourceSuggestionStatus = "pending"
    converted_asset_id: str | None = Field(default=None, min_length=1, max_length=80)
