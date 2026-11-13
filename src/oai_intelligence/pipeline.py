"""Orchestrate discovery, classification, validation, and persistence."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from oai_intelligence.collectors.github import GitHubCollector
from oai_intelligence.collectors.hacker_news import HackerNewsCollector
from oai_intelligence.collectors.rss import RSSCollector, RSSCollectorError
from oai_intelligence.config import load_yaml
from oai_intelligence.models import (
    article_observation,
    discussion_observation,
    repository_observation,
)
from oai_intelligence.storage import append_observations
from oai_intelligence.validation import PROJECT_ROOT, validate_project_configs


def build_github_query(settings: dict[str, Any]) -> str:
    terms = " OR ".join(settings["query_terms"])
    return f"{terms} in:name,description language:{settings['github_language']}"


def _discovery_context(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    validate_project_configs(root)
    source_config = load_yaml(root / "config" / "sources.yaml")
    discovery_config = load_yaml(root / "config" / "discovery.yaml")
    taxonomy = load_yaml(root / "config" / "architecture_taxonomy.yaml")
    return source_config, discovery_config, taxonomy


def _save(
    observations: list[dict[str, Any]],
    observed_at: datetime,
    output_dir: Path | None,
    root: Path,
    dry_run: bool,
) -> tuple[int, Path]:
    destination = output_dir or root / "data" / "observations"
    daily_file = destination / f"{observed_at.date().isoformat()}.jsonl"
    saved = 0 if dry_run else append_observations(daily_file, observations)
    return saved, daily_file


def run_github_discovery(
    limit: int = 10,
    output_dir: Path | None = None,
    dry_run: bool = False,
    root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    source_config, discovery_config, taxonomy = _discovery_context(root)
    github_source = next(
        source
        for source in source_config["sources"]
        if source["id"] == "github" and source["enabled"]
    )
    collector = GitHubCollector(user_agent=source_config["policy"]["user_agent"])
    observed_at = datetime.now(UTC)
    observations: list[dict[str, Any]] = []
    search_counts: dict[str, int] = {}
    candidate_counts: dict[str, int] = {}

    for ecosystem, settings in discovery_config["ecosystems"].items():
        repositories = collector.search_repositories(build_github_query(settings), limit=limit)
        search_counts[ecosystem] = len(repositories)
        candidates = 0
        for repository in repositories:
            observation = repository_observation(repository, ecosystem, taxonomy, observed_at)
            if not observation["architecture_matches"]:
                continue
            observations.append(observation)
            candidates += 1
        candidate_counts[ecosystem] = candidates

    saved, daily_file = _save(observations, observed_at, output_dir, root, dry_run)
    return {
        "source": github_source["id"],
        "search_results_by_ecosystem": search_counts,
        "classified_candidates_by_ecosystem": candidate_counts,
        "search_results": sum(search_counts.values()),
        "classified_candidates": len(observations),
        "new_observations": saved,
        "duplicates_or_existing": len(observations) - saved if not dry_run else 0,
        "dry_run": dry_run,
        "output": str(daily_file) if not dry_run else None,
    }


def run_hacker_news_discovery(
    limit: int = 10,
    output_dir: Path | None = None,
    dry_run: bool = False,
    root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    source_config, discovery_config, taxonomy = _discovery_context(root)
    source = next(
        item for item in source_config["sources"] if item["id"] == "hacker_news" and item["enabled"]
    )
    collector = HackerNewsCollector(user_agent=source_config["policy"]["user_agent"])
    observed_at = datetime.now(UTC)
    queries = list(
        dict.fromkeys(
            term.strip('"')
            for settings in discovery_config["ecosystems"].values()
            for term in settings["query_terms"]
        )
    )
    hits_by_id: dict[str, dict[str, Any]] = {}
    query_counts: dict[str, int] = {}
    for query in queries:
        hits = collector.search_stories(query, limit=limit)
        query_counts[query] = len(hits)
        for hit in hits:
            if isinstance(hit, dict) and hit.get("objectID"):
                hits_by_id[str(hit["objectID"])] = hit

    observations = []
    for hit in hits_by_id.values():
        observation = discussion_observation(hit, taxonomy, observed_at)
        if observation["architecture_matches"]:
            observations.append(observation)

    saved, daily_file = _save(observations, observed_at, output_dir, root, dry_run)
    return {
        "source": source["id"],
        "queries": query_counts,
        "search_results": sum(query_counts.values()),
        "unique_stories": len(hits_by_id),
        "classified_candidates": len(observations),
        "new_observations": saved,
        "duplicates_or_existing": len(observations) - saved if not dry_run else 0,
        "dry_run": dry_run,
        "output": str(daily_file) if not dry_run else None,
    }


def run_rss_discovery(
    limit: int = 20,
    output_dir: Path | None = None,
    dry_run: bool = False,
    root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    source_config, _, taxonomy = _discovery_context(root)
    source = next(
        item for item in source_config["sources"] if item["id"] == "rss" and item["enabled"]
    )
    collector = RSSCollector(user_agent=source_config["policy"]["user_agent"])
    observed_at = datetime.now(UTC)
    feed_results: dict[str, int] = {}
    feed_errors: dict[str, str] = {}
    articles_by_url: dict[str, dict[str, Any]] = {}

    for feed in source["feeds"]:
        feed_id = str(feed["id"])
        try:
            articles = collector.fetch_feed(feed, limit=limit)
            feed_results[feed_id] = len(articles)
            for article in articles:
                # Canonical article URL deduplicates the same story syndicated by multiple feeds.
                articles_by_url.setdefault(article["url"], article)
        except RSSCollectorError as exc:
            feed_errors[feed_id] = str(exc)

    if feed_errors and not feed_results:
        details = "; ".join(f"{key}: {value}" for key, value in feed_errors.items())
        raise RSSCollectorError(f"All configured RSS feeds failed. {details}")

    observations = []
    for article in articles_by_url.values():
        observation = article_observation(article, taxonomy, observed_at)
        if observation["architecture_matches"]:
            observations.append(observation)

    saved, daily_file = _save(observations, observed_at, output_dir, root, dry_run)
    return {
        "source": source["id"],
        "feeds": feed_results,
        "feed_errors": feed_errors,
        "articles_fetched": sum(feed_results.values()),
        "unique_articles": len(articles_by_url),
        "classified_candidates": len(observations),
        "new_observations": saved,
        "duplicates_or_existing": len(observations) - saved if not dry_run else 0,
        "dry_run": dry_run,
        "output": str(daily_file) if not dry_run else None,
    }


def run_all_discovery(
    limit: int = 10,
    output_dir: Path | None = None,
    dry_run: bool = False,
    root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    results = {
        "github": run_github_discovery(limit, output_dir, dry_run, root),
        "hacker_news": run_hacker_news_discovery(limit, output_dir, dry_run, root),
        "rss": run_rss_discovery(limit, output_dir, dry_run, root),
    }
    return {
        "sources": results,
        "total_search_results": sum(
            item.get("search_results", item.get("articles_fetched", 0)) for item in results.values()
        ),
        "total_candidates": sum(item["classified_candidates"] for item in results.values()),
        "total_new_observations": sum(item["new_observations"] for item in results.values()),
        "dry_run": dry_run,
    }
