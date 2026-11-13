import io
import json
from unittest.mock import patch
from urllib.error import URLError

import pytest

from oai_intelligence.collectors.hacker_news import (
    HackerNewsCollector,
    HackerNewsCollectorError,
)


def test_search_stories_uses_algolia_search_endpoint() -> None:
    payload = {"hits": [{"objectID": "123", "title": "Microservices"}]}
    response = io.BytesIO(json.dumps(payload).encode())
    collector = HackerNewsCollector(user_agent="OAI-tests")

    with patch(
        "oai_intelligence.collectors.hacker_news.urlopen", return_value=response
    ) as mocked:
        result = collector.search_stories("microservices", limit=5)

    request = mocked.call_args.args[0]
    assert request.full_url.startswith(
        "https://hn.algolia.com/api/v1/search_by_date?"
    )
    assert "tags=story" in request.full_url
    assert request.get_header("User-agent") == "OAI-tests"
    assert result == payload["hits"]


def test_search_stories_retries_temporary_network_errors() -> None:
    payload = {"hits": [{"objectID": "123"}]}
    response = io.BytesIO(json.dumps(payload).encode())
    collector = HackerNewsCollector(user_agent="OAI-tests")
    with (
        patch(
            "oai_intelligence.collectors.hacker_news.urlopen",
            side_effect=[URLError("temporary"), response],
        ) as mocked,
        patch("oai_intelligence.collectors.hacker_news.time.sleep"),
    ):
        assert collector.search_stories("microservices") == payload["hits"]
    assert mocked.call_count == 2


def test_search_stories_rejects_invalid_limit() -> None:
    collector = HackerNewsCollector(user_agent="OAI-tests")
    with pytest.raises(ValueError, match="between 1 and 100"):
        collector.search_stories("python", limit=101)


def test_invalid_search_payload_is_rejected() -> None:
    response = io.BytesIO(b'{"unexpected": []}')
    collector = HackerNewsCollector(user_agent="OAI-tests")
    with (
        patch(
            "oai_intelligence.collectors.hacker_news.urlopen",
            return_value=response,
        ),
        pytest.raises(HackerNewsCollectorError, match="hits list"),
    ):
        collector.search_stories("python")
