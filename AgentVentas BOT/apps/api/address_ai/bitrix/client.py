from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


class BitrixError(RuntimeError):
    pass


class BitrixClient:
    def __init__(self, webhook_base_url: str, timeout_seconds: int = 15) -> None:
        self.webhook_base_url = webhook_base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def call(self, method: str, params: dict[str, Any]) -> Any:
        url = f"{self.webhook_base_url}/{method}.json"
        payload = json.dumps(params).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=payload,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            raise BitrixError(f"HTTP {error.code} calling {method}: {body}") from error
        except urllib.error.URLError as error:
            raise BitrixError(f"Network error calling {method}: {error.reason}") from error

        data = json.loads(body)
        if "error" in data:
            description = data.get("error_description") or data["error"]
            raise BitrixError(f"{method}: {description}")

        return data.get("result")
