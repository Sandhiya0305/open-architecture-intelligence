import io
from unittest.mock import patch

import pytest

from oai_intelligence.collectors.rss import RSSCollector, RSSCollectorError

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


def test_fetches_and_parses_rss_items() -> None:
    collector = RSSCollector(user_agent="OAI-tests")
    feed = {"id": "example", "publisher": "Example Publisher", "url": "https://example.com/feed"}
    with patch(
        "oai_intelligence.collectors.rss.urlopen",
        return_value=io.BytesIO(RSS_XML),
    ) as mocked:
        items = collector.fetch_feed(feed, limit=5)

    assert len(items) == 1
    assert items[0]["title"] == "Clean Architecture with Python"
    assert items[0]["entry_id"] == "article-1"
    assert items[0]["published_at"] == "2026-11-12T10:00:00Z"
    assert "practical architecture article" in items[0]["summary"]
    assert items[0]["publisher"] == "Example Publisher"
    assert mocked.call_args.args[0].get_header("User-agent") == "OAI-tests"


def test_fetches_and_parses_atom_entries() -> None:
    collector = RSSCollector(user_agent="OAI-tests")
    feed = {"id": "atom", "url": "https://example.com/feed.atom"}
    with patch(
        "oai_intelligence.collectors.rss.urlopen",
        return_value=io.BytesIO(ATOM_XML),
    ):
        items = collector.fetch_feed(feed)

    assert items[0]["title"] == "Event-Driven Architecture Patterns"
    assert items[0]["url"] == "https://example.com/events"
    assert items[0]["author"] == "Example Author"
    assert items[0]["published_at"] == "2026-11-12T11:00:00Z"


def test_invalid_xml_is_rejected() -> None:
    collector = RSSCollector(user_agent="OAI-tests")
    with (
        patch(
            "oai_intelligence.collectors.rss.urlopen",
            return_value=io.BytesIO(b"<not-valid"),
        ),
        pytest.raises(RSSCollectorError, match="invalid XML"),
    ):
        collector.fetch_feed({"id": "broken", "url": "https://example.com/feed"})


def test_non_https_feed_is_rejected() -> None:
    collector = RSSCollector(user_agent="OAI-tests")
    with pytest.raises(ValueError, match="HTTPS"):
        collector.fetch_feed({"id": "unsafe", "url": "http://example.com/feed"})
