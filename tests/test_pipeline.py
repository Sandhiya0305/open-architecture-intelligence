from oai_intelligence.config import load_yaml
from oai_intelligence.pipeline import build_github_query
from oai_intelligence.validation import PROJECT_ROOT


def test_github_query_uses_broad_discovery_terms_and_language_filter() -> None:
    query = build_github_query(
        {
            "query_terms": [
                '"software architecture"',
                '"system design"',
                '"application architecture"',
                '"distributed systems"',
            ],
            "github_language": "Python",
        }
    )
    assert query == (
        '"software architecture" OR "system design" OR "application architecture" '
        'OR "distributed systems" in:name,description language:Python'
    )
    assert "microservices" not in query
    assert "readme" not in query


def test_discovery_terms_are_not_the_taxonomy_match_terms():
    discovery = load_yaml(PROJECT_ROOT / "config" / "discovery.yaml")
    taxonomy = load_yaml(PROJECT_ROOT / "config" / "architecture_taxonomy.yaml")
    match_terms = {
        term.casefold()
        for architecture in taxonomy["architectures"]
        for term in [architecture["name"], *architecture.get("aliases", [])]
    }
    for settings in discovery["ecosystems"].values():
        assert all(term.strip('"').casefold() not in match_terms for term in settings["query_terms"])
