"""RSS and Atom feed collection using Python's standard library."""

import time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class RSSCollectorError(RuntimeError):
    """Raised when a configured feed cannot be fetched or parsed."""


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        return " ".join(" ".join(self.parts).split())


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].split(":")[-1].casefold()


def _child_text(element: ET.Element, names: set[str]) -> str:
    for child in element.iter():
        if child is element or _local_name(child.tag) not in names:
            continue
        value = " ".join("".join(child.itertext()).split())
        if value:
            return value
    return ""


def _clean_summary(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(unescape(value))
    return parser.text()


def _parse_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _entry_link(entry: ET.Element) -> str:
    for child in entry:
        if _local_name(child.tag) != "link":
            continue
        href = child.attrib.get("href")
        if href and child.attrib.get("rel", "alternate") == "alternate":
            return href
        if child.text and child.text.strip():
            return child.text.strip()
    return ""


class RSSCollector:
    def __init__(self, user_agent: str, timeout: float = 20.0, max_attempts: int = 3) -> None:
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_attempts = max_attempts

    def fetch_feed(self, feed: dict[str, Any], limit: int = 20) -> list[dict[str, Any]]:
        if not 1 <= limit <= 100:
            raise ValueError("RSS feed limit must be between 1 and 100.")
        feed_id = str(feed.get("id") or "unknown")
        url = str(feed.get("url") or "")
        if not url.startswith("https://"):
            raise ValueError(f"Feed {feed_id} must use an HTTPS URL.")

        request = Request(
            url,
            headers={
                "Accept": "application/atom+xml, application/rss+xml, application/xml, text/xml",
                "User-Agent": self.user_agent,
            },
        )
        payload: bytes | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    payload = response.read()
                break
            except HTTPError as exc:
                if exc.code not in {429, 500, 502, 503, 504} or attempt == self.max_attempts:
                    raise RSSCollectorError(f"Feed {feed_id} returned HTTP {exc.code}.") from exc
                time.sleep(attempt)
            except (URLError, TimeoutError, OSError) as exc:
                if attempt == self.max_attempts:
                    raise RSSCollectorError(
                        f"Could not fetch feed {feed_id} after {self.max_attempts} attempts: {exc}"
                    ) from exc
                time.sleep(attempt)

        if payload is None:
            raise RSSCollectorError(f"Feed {feed_id} returned no content.")
        try:
            root = ET.fromstring(payload)
        except ET.ParseError as exc:
            raise RSSCollectorError(f"Feed {feed_id} contains invalid XML: {exc}") from exc

        feed_title = _child_text(root, {"title"}) or str(feed.get("publisher") or feed_id)
        entries = [
            element for element in root.iter() if _local_name(element.tag) in {"item", "entry"}
        ]
        records: list[dict[str, Any]] = []
        for entry in entries[:limit]:
            title = _child_text(entry, {"title"})
            link = _entry_link(entry)
            if not title or not link.startswith("https://"):
                continue
            summary = _child_text(entry, {"summary", "description", "encoded", "content"})
            author = _child_text(entry, {"creator", "author", "name"})
            published = _child_text(entry, {"published", "updated", "pubdate", "date"})
            guid = _child_text(entry, {"guid", "id"}) or link
            records.append(
                {
                    "feed_id": feed_id,
                    "feed_title": feed_title,
                    "publisher": str(feed.get("publisher") or feed_title),
                    "entry_id": guid,
                    "title": title,
                    "url": link,
                    "summary": _clean_summary(summary),
                    "author": author or None,
                    "published_at": _parse_date(published),
                }
            )
        return records
