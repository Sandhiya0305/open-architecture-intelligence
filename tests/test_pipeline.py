from oai_intelligence.pipeline import build_github_query


def test_github_query_uses_or_terms_and_language_filter() -> None:
    query = build_github_query(
        {
            "query_terms": ["microservices", '"clean architecture"', '"event-driven"'],
            "github_language": "Python",
        }
    )
    assert query == (
        'microservices OR "clean architecture" OR "event-driven" '
        "in:name,description language:Python"
    )
    assert "readme" not in query
