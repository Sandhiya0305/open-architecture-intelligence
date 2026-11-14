# Collector fixtures

These small fixtures preserve representative public response shapes for regression tests.

- `github_search_response.json`: selected fields from GitHub's public repository search API, captured 14 November 2026. The example repository is archived; the fixture intentionally preserves that flag.
- `hacker_news_search_response.json`: selected fields from the Algolia Hacker News Search API, captured 14 November 2026.
- `martin_fowler_first_entry.atom`: one metadata-only Atom entry from the public Martin Fowler feed, captured 14 November 2026. The full article body is not included.

The tests mock network access. These fixtures test parsing against representative real response structures without making the test suite depend on live services.
