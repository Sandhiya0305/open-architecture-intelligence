"""Orchestrate discovery, classification, validation, and persistence."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from oai_intelligence.collectors.github import GitHubCollector
from oai_intelligence.config import load_yaml
from oai_intelligence.models import repository_observation
from oai_intelligence.storage import append_observations
from oai_intelligence.validation import PROJECT_ROOT, validate_project_configs


def build_github_query(settings: dict[str, Any]) -> str:
    terms = " OR ".join(settings["query_terms"])
    return f"{terms} in:name,description language:{settings['github_language']}"


def run_github_discovery(
    limit: int = 10,
    output_dir: Path | None = None,
    dry_run: bool = False,
    root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    validate_project_configs(root)
    source_config = load_yaml(root / "config" / "sources.yaml")
    discovery_config = load_yaml(root / "config" / "discovery.yaml")
    taxonomy = load_yaml(root / "config" / "architecture_taxonomy.yaml")
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

    destination = output_dir or root / "data" / "observations"
    daily_file = destination / f"{observed_at.date().isoformat()}.jsonl"
    saved = 0 if dry_run else append_observations(daily_file, observations)
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
