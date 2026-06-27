from __future__ import annotations

from hashlib import sha256
from typing import TYPE_CHECKING

import orjson

if TYPE_CHECKING:
    from services.gateway.pipeline_v2_store import PipelineV2EventRead
    from services.gateway.pipeline_v2_types import JsonObject


def format_event_stream(event: PipelineV2EventRead) -> str:
    payload = event.payload or {}
    data = orjson.dumps({"sequence": event.sequence, **payload}).decode()
    return f"id: {event.sequence}\nevent: {event.event_name}\ndata: {data}\n\n"


def hash_json(payload: JsonObject) -> str:
    return sha256(orjson.dumps(payload, option=orjson.OPT_SORT_KEYS)).hexdigest()
