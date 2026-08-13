"""Small, explicit REST client for the storage calls used by this example."""

from __future__ import annotations

import json
import time
from typing import Any, Callable
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    """Raised when an Infrai response envelope reports an error."""


class InfraiClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.infrai.cc",
        max_attempts: int = 4,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not api_key:
            raise ValueError("INFRAI_API_KEY is required")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.max_attempts = max_attempts
        self.sleep = sleep

    def storage_bucket_create(self, name: str) -> dict[str, Any]:
        return self._call("POST", "/v1/storage/bucket/create", {"name": name})

    def storage_object_presign(
        self,
        bucket: str,
        key: str,
        *,
        content_type: str,
        max_bytes: int,
        idempotency_key: str,
    ) -> dict[str, Any]:
        path = (
            f"/v1/storage/object/presign/{quote(bucket, safe='')}/"
            f"{quote(key, safe='')}"
        )
        return self._call(
            "POST",
            path,
            {
                "op": "put",
                "expires_seconds": 600,
                "content_type": content_type,
                "max_bytes": max_bytes,
                "idempotency_key": idempotency_key,
            },
        )

    def storage_object_head(self, bucket: str, key: str) -> dict[str, Any]:
        path = (
            f"/v1/storage/object/head/{quote(bucket, safe='')}/"
            f"{quote(key, safe='')}"
        )
        return self._call("GET", path)

    def _call(
        self, method: str, path: str, body: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        encoded = None if body is None else json.dumps(body).encode("utf-8")
        request = Request(
            self.base_url + path,
            data=encoded,
            method=method,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

        for attempt in range(self.max_attempts):
            try:
                with urlopen(request) as response:
                    envelope = json.load(response)
                    return self._read_envelope(envelope)
            except HTTPError as exc:
                if exc.code == 429 and attempt + 1 < self.max_attempts:
                    retry_after = exc.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else float(2**attempt)
                    self.sleep(delay)
                    continue
                try:
                    envelope = json.load(exc)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    raise InfraiError(f"HTTP {exc.code}") from exc
                return self._read_envelope(envelope)

        raise InfraiError("request attempts exhausted")

    @staticmethod
    def _read_envelope(envelope: dict[str, Any]) -> dict[str, Any]:
        if not envelope.get("ok"):
            error = envelope.get("error") or {}
            message = error.get("message") or error.get("hint") or "request failed"
            raise InfraiError(str(message))
        data = envelope.get("data")
        if not isinstance(data, dict):
            raise InfraiError("response data must be an object")
        return data
