from __future__ import annotations

from hashlib import sha256
from typing import TYPE_CHECKING

import orjson

if TYPE_CHECKING:
    from services.gateway.teaching_pack_store import TeachingPackEventRead
    from services.gateway.teaching_pack_types import JsonObject


def format_event_stream(event: TeachingPackEventRead) -> str:
    payload = event.payload or {}
    data = orjson.dumps({"sequence": event.sequence, **payload}).decode()
    return f"id: {event.sequence}\nevent: {event.event_name}\ndata: {data}\n\n"


def hash_json(payload: JsonObject) -> str:
    return sha256(orjson.dumps(payload, option=orjson.OPT_SORT_KEYS)).hexdigest()
