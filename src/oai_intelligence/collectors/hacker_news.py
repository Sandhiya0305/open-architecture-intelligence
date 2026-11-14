"""Hacker News story discovery through the Algolia HN Search API."""

import json
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

MAX_RESPONSE_BYTES = 5 * 1024 * 1024


class HackerNewsCollectorError(RuntimeError):
    """Raised when Hacker News search cannot provide a valid response."""


class HackerNewsCollector:
    API_ROOT = "https://hn.algolia.com/api/v1"

    def __init__(
        self,
        user_agent: str,
        timeout: float = 20.0,
        max_attempts: int = 3,
        max_response_bytes: int = MAX_RESPONSE_BYTES,
    ) -> None:
        if max_response_bytes < 1:
            raise ValueError("max_response_bytes must be positive.")
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_attempts = max_attempts
        self.max_response_bytes = max_response_bytes

    def search_stories(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        if not 1 <= limit <= 100:
            raise ValueError("Hacker News search limit must be between 1 and 100.")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1.")
        params = urlencode({"query": query, "tags": "story", "hitsPerPage": limit})
        request = Request(
            f"{self.API_ROOT}/search_by_date?{params}",
            headers={"Accept": "application/json", "User-Agent": self.user_agent},
        )
        for attempt in range(1, self.max_attempts + 1):
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    payload_bytes = response.read(self.max_response_bytes + 1)
                if len(payload_bytes) > self.max_response_bytes:
                    raise HackerNewsCollectorError(
                        f"Hacker News response exceeded the {self.max_response_bytes}-byte limit."
                    )
                payload = json.loads(payload_bytes)
                break
            except HTTPError as exc:
                if exc.code not in {429, 500, 502, 503, 504} or attempt == self.max_attempts:
                    raise HackerNewsCollectorError(
                        f"Hacker News search API returned HTTP {exc.code}."
                    ) from exc
                time.sleep(attempt)
            except (URLError, TimeoutError, OSError) as exc:
                if attempt == self.max_attempts:
                    raise HackerNewsCollectorError(
                        f"Could not reach Hacker News search API after "
                        f"{self.max_attempts} attempts: {exc}"
                    ) from exc
                time.sleep(attempt)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise HackerNewsCollectorError(
                    f"Hacker News search API returned invalid JSON: {exc}"
                ) from exc
        else:
            raise HackerNewsCollectorError("Hacker News search attempts were exhausted.")

        hits = payload.get("hits") if isinstance(payload, dict) else None
        if not isinstance(hits, list):
            raise HackerNewsCollectorError(
                "Hacker News search response did not contain a hits list."
            )
        return hits
