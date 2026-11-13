"""GitHub repository discovery using the public REST API."""

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class GitHubCollectorError(RuntimeError):
    """Raised when GitHub cannot provide a valid discovery response."""


class GitHubCollector:
    API_ROOT = "https://api.github.com"

    def __init__(
        self,
        user_agent: str,
        token: str | None = None,
        timeout: float = 20.0,
    ) -> None:
        self.user_agent = user_agent
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.timeout = timeout

    def search_repositories(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        if not 1 <= limit <= 100:
            raise ValueError("GitHub search limit must be between 1 and 100.")
        params = urlencode(
            {"q": query, "sort": "updated", "order": "desc", "per_page": limit}
        )
        request = Request(
            f"{self.API_ROOT}/search/repositories?{params}",
            headers=self._headers(),
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.load(response)
        except HTTPError as exc:
            if exc.code in {403, 429}:
                reset = exc.headers.get("X-RateLimit-Reset", "unknown")
                raise GitHubCollectorError(
                    f"GitHub API rate limit or access restriction (HTTP {exc.code}); "
                    f"rate-limit reset epoch: {reset}. Set GITHUB_TOKEN for a higher quota."
                ) from exc
            raise GitHubCollectorError(f"GitHub API returned HTTP {exc.code}.") from exc
        except (URLError, TimeoutError) as exc:
            raise GitHubCollectorError(f"Could not reach GitHub API: {exc}") from exc
        except (json.JSONDecodeError, OSError) as exc:
            raise GitHubCollectorError(f"GitHub returned an invalid response: {exc}") from exc

        items = payload.get("items") if isinstance(payload, dict) else None
        if not isinstance(items, list):
            raise GitHubCollectorError("GitHub search response did not contain an items list.")
        return items

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": self.user_agent,
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
