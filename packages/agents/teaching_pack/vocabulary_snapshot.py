from __future__ import annotations

import hashlib
import json

from common.contracts.run_contract import JsonObject


def vocabulary_cluster_snapshot_hash(payload: JsonObject) -> str:
    canonical_payload = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()
