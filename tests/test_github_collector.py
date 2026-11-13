import io
import json
from unittest.mock import patch

import pytest

from oai_intelligence.collectors.github import GitHubCollector, GitHubCollectorError


def test_search_repositories_sends_expected_query_and_headers() -> None:
    payload = {"items": [{"full_name": "example/service"}]}
    response = io.BytesIO(json.dumps(payload).encode())
    collector = GitHubCollector(user_agent="OAI-tests")

    with patch("oai_intelligence.collectors.github.urlopen", return_value=response) as mocked:
        result = collector.search_repositories("microservices language:Python", limit=5)

    request = mocked.call_args.args[0]
    assert "microservices" in request.full_url
    assert request.get_header("User-agent") == "OAI-tests"
    assert result == payload["items"]


def test_search_rejects_invalid_limit() -> None:
    collector = GitHubCollector(user_agent="OAI-tests")
    with pytest.raises(ValueError, match="between 1 and 100"):
        collector.search_repositories("python", limit=101)


def test_invalid_api_payload_is_rejected() -> None:
    response = io.BytesIO(b'{"message": "unexpected response"}')
    collector = GitHubCollector(user_agent="OAI-tests")
    with (
        patch("oai_intelligence.collectors.github.urlopen", return_value=response),
        pytest.raises(GitHubCollectorError, match="items list"),
    ):
        collector.search_repositories("python")
