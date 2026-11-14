import io
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

import pytest

from oai_intelligence.collectors.rss import RSSCollector, RSSCollectorError

ROBOTS_ALLOW = b"User-agent: *\nAllow: /\n"

RSS_XML = b"""<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Example Engineering</title>
    <item>
      <title>Clean Architecture with Python</title>
      <link>https://example.com/clean-architecture</link>
      <guid>article-1</guid>
      <pubDate>Thu, 12 Nov 2026 10:00:00 GMT</pubDate>
      <description><![CDATA[<p>A practical <b>architecture</b> article.</p>]]></description>
      <author>writer@example.com</author>
    </item>
  </channel>
</rss>"""

ATOM_XML = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Example Atom</title>
  <entry>
    <id>tag:example.com,2026:article-2</id>
    <title>Event-Driven Architecture Patterns</title>
    <link href="https://example.com/events" rel="alternate" />
    <updated>2026-11-12T11:00:00Z</updated>
    <summary>Event processing patterns.</summary>
    <author><name>Example Author</name></author>
  </entry>
</feed>"""


def test_fetches_and_parses_rss_items_and_checks_robots() -> None:
    collector = RSSCollector(user_agent="OAI-tests")
    feed = {
        "id": "example",
        "publisher": "Example Publisher",
        "publisher_type": "editorial",
        "url": "https://example.com/feed",
    }
    with patch(
        "oai_intelligence.collectors.rss.urlopen",
        side_effect=[io.BytesIO(ROBOTS_ALLOW), io.BytesIO(RSS_XML)],
    ) as mocked:
        items = collector.fetch_feed(feed, limit=5)

    assert len(items) == 1
    assert items[0]["title"] == "Clean Architecture with Python"
    assert items[0]["entry_id"] == "article-1"
    assert items[0]["published_at"] == "2026-11-12T10:00:00Z"
    assert "practical architecture article" in items[0]["summary"]
    assert items[0]["publisher"] == "Example Publisher"
    assert items[0]["publisher_type"] == "editorial"
    assert mocked.call_count == 2
    assert mocked.call_args_list[0].args[0].full_url == "https://example.com/robots.txt"
    assert mocked.call_args_list[0].args[0].get_header("User-agent") == "OAI-tests"


def test_fetches_and_parses_atom_entries() -> None:
    collector = RSSCollector(user_agent="OAI-tests")
    feed = {"id": "atom", "url": "https://example.com/feed.atom"}
    with patch(
        "oai_intelligence.collectors.rss.urlopen",
        side_effect=[io.BytesIO(ROBOTS_ALLOW), io.BytesIO(ATOM_XML)],
    ):
        items = collector.fetch_feed(feed)

    assert items[0]["title"] == "Event-Driven Architecture Patterns"
    assert items[0]["url"] == "https://example.com/events"
    assert items[0]["author"] == "Example Author"
    assert items[0]["published_at"] == "2026-11-12T11:00:00Z"
    assert items[0]["summary"] == "Event processing patterns."


def test_does_not_treat_full_atom_content_as_a_summary() -> None:
    xml = ATOM_XML.replace(
        b"<summary>Event processing patterns.</summary>",
        b'<content type="html"><![CDATA['
        b"<p>Full article text about event-driven architecture.</p>"
        b"]]></content>",
    )
    collector = RSSCollector(user_agent="OAI-tests")
    with patch(
        "oai_intelligence.collectors.rss.urlopen",
        side_effect=[io.BytesIO(ROBOTS_ALLOW), io.BytesIO(xml)],
    ):
        items = collector.fetch_feed({"id": "atom", "url": "https://example.com/feed.atom"})

    assert len(items) == 1
    assert items[0]["summary"] == ""


def test_robots_disallow_prevents_feed_request() -> None:
    collector = RSSCollector(user_agent="OAI-tests")
    robots = b"User-agent: *\nDisallow: /feed\n"
    with (
        patch("oai_intelligence.collectors.rss.urlopen", return_value=io.BytesIO(robots)) as mocked,
        pytest.raises(RSSCollectorError, match="disallowed by robots.txt"),
    ):
        collector.fetch_feed({"id": "blocked", "url": "https://example.com/feed"})

    assert mocked.call_count == 1


def test_robots_network_failure_fails_closed() -> None:
    collector = RSSCollector(user_agent="OAI-tests")
    with (
        patch("oai_intelligence.collectors.rss.urlopen", side_effect=URLError("offline")),
        pytest.raises(RSSCollectorError, match="refusing to fetch"),
    ):
        collector.fetch_feed({"id": "offline", "url": "https://example.com/feed"})


def test_invalid_xml_is_rejected() -> None:
    collector = RSSCollector(user_agent="OAI-tests")
    with (
        patch(
            "oai_intelligence.collectors.rss.urlopen",
            side_effect=[io.BytesIO(ROBOTS_ALLOW), io.BytesIO(b"<not-valid")],
        ),
        pytest.raises(RSSCollectorError, match="invalid or unsafe XML"),
    ):
        collector.fetch_feed({"id": "broken", "url": "https://example.com/feed"})


def test_feed_response_size_is_bounded() -> None:
    collector = RSSCollector(user_agent="OAI-tests", max_response_bytes=10)
    with (
        patch(
            "oai_intelligence.collectors.rss.urlopen",
            side_effect=[io.BytesIO(ROBOTS_ALLOW), io.BytesIO(RSS_XML)],
        ),
        pytest.raises(RSSCollectorError, match="byte limit"),
    ):
        collector.fetch_feed({"id": "large", "url": "https://example.com/feed"})


def test_non_https_feed_is_rejected() -> None:
    collector = RSSCollector(user_agent="OAI-tests")
    with pytest.raises(ValueError, match="HTTPS"):
        collector.fetch_feed({"id": "unsafe", "url": "http://example.com/feed"})


def test_parses_captured_public_atom_feed_entry():
    atom_fixture = (Path(__file__).parent / "fixtures/martin_fowler_first_entry.atom").read_bytes()
    collector = RSSCollector(user_agent="OAI-tests")
    feed = {
        "id": "martin_fowler",
        "publisher": "Martin Fowler",
        "publisher_type": "practitioner",
        "url": "https://martinfowler.com/feed.atom",
    }

    with patch(
        "oai_intelligence.collectors.rss.urlopen",
        side_effect=[io.BytesIO(ROBOTS_ALLOW), io.BytesIO(atom_fixture)],
    ):
        items = collector.fetch_feed(feed, limit=1)

    assert len(items) == 1
    assert items[0]["title"] == "Bliki: Generated Glossary"
    assert items[0]["url"] == "https://martinfowler.com/bliki/GeneratedGlossary.html"
    assert items[0]["publisher_type"] == "practitioner"
