from __future__ import annotations

import socket
from dataclasses import dataclass
from typing import Final
from urllib.parse import urlparse

type BreakerValue = float | int | str
type RedisResponse = str | int | None | list[RedisResponse]

_DEFAULT_REDIS_URL: Final = "redis://localhost:6379/0"


@dataclass(frozen=True, slots=True)
class RedisAddress:
    host: str
    port: int
    db: int


class RedisBreakerStore:
    def __init__(self, address: RedisAddress | None = None, timeout_seconds: float = 0.25) -> None:
        self._address = address or parse_redis_url(_DEFAULT_REDIS_URL)
        self._timeout_seconds = timeout_seconds

    @classmethod
    def from_url(cls, url: str, timeout_seconds: float = 0.25) -> RedisBreakerStore:
        return cls(parse_redis_url(url), timeout_seconds=timeout_seconds)

    def get(self, key: str) -> dict[str, BreakerValue] | None:
        response = self._execute("HGETALL", key)
        if not isinstance(response, list) or not response:
            return None
        values: dict[str, BreakerValue] = {}
        for index in range(0, len(response), 2):
            field = response[index]
            value = response[index + 1]
            if isinstance(field, str) and isinstance(value, str):
                values[field] = value
        return values

    def set(self, key: str, value: dict[str, BreakerValue], ttl_seconds: float) -> None:
        command = ["HSET", key]
        for field, field_value in value.items():
            command.extend((field, str(field_value)))
        self._execute(*command)
        self._execute("EXPIRE", key, str(max(1, int(ttl_seconds))))

    def ping(self) -> bool:
        return self._execute("PING") == "PONG"

    def delete(self, key: str) -> None:
        self._execute("DEL", key)

    def _execute(self, *parts: str) -> RedisResponse:
        with socket.create_connection(
            (self._address.host, self._address.port),
            timeout=self._timeout_seconds,
        ) as connection:
            connection.settimeout(self._timeout_seconds)
            if self._address.db:
                connection.sendall(_command("SELECT", str(self._address.db)))
                _read_response(connection)
            connection.sendall(_command(*parts))
            return _read_response(connection)


def parse_redis_url(url: str) -> RedisAddress:
    parsed = urlparse(url)
    db_text = parsed.path.lstrip("/") or "0"
    return RedisAddress(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        db=int(db_text),
    )


def _command(*parts: str) -> bytes:
    payload = [f"*{len(parts)}\r\n".encode()]
    for part in parts:
        encoded = part.encode("utf-8")
        payload.append(f"${len(encoded)}\r\n".encode())
        payload.append(encoded + b"\r\n")
    return b"".join(payload)


def _read_response(connection: socket.socket) -> RedisResponse:
    prefix = _read_exact(connection, 1)
    match prefix:
        case b"+":
            return _read_line(connection)
        case b":":
            return int(_read_line(connection))
        case b"$":
            length = int(_read_line(connection))
            if length == -1:
                return None
            data = _read_exact(connection, length)
            _read_exact(connection, 2)
            return data.decode("utf-8")
        case b"*":
            count = int(_read_line(connection))
            return [_read_response(connection) for _ in range(count)]
        case b"-":
            raise ConnectionError(_read_line(connection))
        case unreachable:
            raise ConnectionError(f"unexpected redis response prefix: {unreachable!r}")


def _read_line(connection: socket.socket) -> str:
    chunks: list[bytes] = []
    while True:
        char = _read_exact(connection, 1)
        if char == b"\r":
            _read_exact(connection, 1)
            return b"".join(chunks).decode("utf-8")
        chunks.append(char)


def _read_exact(connection: socket.socket, size: int) -> bytes:
    data = connection.recv(size)
    if len(data) != size:
        raise ConnectionError("short redis response")
    return data
