"""RSS and Atom discovery with bounded responses and robots.txt enforcement."""

import time
import xml.etree.ElementTree as StdET
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

from defusedxml import ElementTree as ET
from defusedxml.common import DefusedXmlException

MAX_FEED_BYTES = 2 * 1024 * 1024
MAX_ROBOTS_BYTES = 512 * 1024


class RSSCollectorError(RuntimeError):
    """Raised when a configured feed cannot be fetched or parsed safely."""


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        return " ".join(" ".join(self.parts).split())


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].split(":")[-1].casefold()


def _child_text(element: StdET.Element, names: set[str]) -> str:
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


def _entry_link(entry: StdET.Element) -> str:
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
    def __init__(
        self,
        user_agent: str,
        timeout: float = 20.0,
        max_attempts: int = 3,
        max_response_bytes: int = MAX_FEED_BYTES,
        max_robots_bytes: int = MAX_ROBOTS_BYTES,
    ) -> None:
        if max_response_bytes < 1 or max_robots_bytes < 1:
            raise ValueError("Response size limits must be positive.")
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1.")
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_attempts = max_attempts
        self.max_response_bytes = max_response_bytes
        self.max_robots_bytes = max_robots_bytes
        self._robots_cache: dict[str, RobotFileParser] = {}

    def _robots_parser(self, feed_url: str) -> RobotFileParser:
        parsed = urlsplit(feed_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin in self._robots_cache:
            return self._robots_cache[origin]

        robots_url = f"{origin}/robots.txt"
        request = Request(robots_url, headers={"User-Agent": self.user_agent})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                content = response.read(self.max_robots_bytes + 1)
            if len(content) > self.max_robots_bytes:
                raise RSSCollectorError(
                    f"robots.txt for {origin} exceeded the {self.max_robots_bytes}-byte limit."
                )
            lines = content.decode("utf-8", errors="replace").splitlines()
        except HTTPError as exc:
            if exc.code == 404:
                lines = []
            elif exc.code in {401, 403} or 500 <= exc.code < 600:
                lines = ["User-agent: *", "Disallow: /"]
            elif 400 <= exc.code < 500:
                lines = []
            else:
                raise RSSCollectorError(
                    f"Could not read robots.txt for {origin}: HTTP {exc.code}."
                ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise RSSCollectorError(
                f"Could not read robots.txt for {origin}; refusing to fetch the feed: {exc}"
            ) from exc

        parser = RobotFileParser(robots_url)
        parser.parse(lines)
        self._robots_cache[origin] = parser
        return parser

    def fetch_feed(self, feed: dict[str, Any], limit: int = 20) -> list[dict[str, Any]]:
        if not 1 <= limit <= 100:
            raise ValueError("RSS feed limit must be between 1 and 100.")
        feed_id = str(feed.get("id") or "unknown")
        url = str(feed.get("url") or "")
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError(f"Feed {feed_id} must use an HTTPS URL.")

        robots = self._robots_parser(url)
        if not robots.can_fetch(self.user_agent, url):
            raise RSSCollectorError(f"Feed {feed_id} is disallowed by robots.txt.")

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
                    payload = response.read(self.max_response_bytes + 1)
                if len(payload) > self.max_response_bytes:
                    raise RSSCollectorError(
                        f"Feed {feed_id} exceeded the {self.max_response_bytes}-byte limit."
                    )
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
        except (StdET.ParseError, DefusedXmlException, ValueError) as exc:
            raise RSSCollectorError(
                f"Feed {feed_id} contains invalid or unsafe XML: {exc}"
            ) from exc

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
                    "publisher_type": str(feed.get("publisher_type") or "unspecified"),
                    "entry_id": guid,
                    "title": title,
                    "url": link,
                    "summary": _clean_summary(summary),
                    "author": author or None,
                    "published_at": _parse_date(published),
                }
            )
        return records
