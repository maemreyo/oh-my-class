from __future__ import annotations

import hashlib
import json

from packages.agents.teaching_pack.scoped_repair_models import JsonObject


def content_hash(artifact: JsonObject) -> str:
    payload = json.dumps(artifact, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
