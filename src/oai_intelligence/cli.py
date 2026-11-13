"""Command-line interface for Open Architecture Intelligence."""

import argparse
import json
import sys
from pathlib import Path

from oai_intelligence import __version__
from oai_intelligence.collectors.github import GitHubCollectorError
from oai_intelligence.collectors.hacker_news import HackerNewsCollectorError
from oai_intelligence.pipeline import (
    run_all_discovery,
    run_github_discovery,
    run_hacker_news_discovery,
)
from oai_intelligence.validation import validate_project_configs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="oai", description="Evidence-first software architecture intelligence."
    )
    parser.add_argument("--version", action="version", version=f"OAI {__version__}")
    commands = parser.add_subparsers(dest="command")

    commands.add_parser("status", help="Show project foundation status")
    commands.add_parser("validate-config", help="Validate source and discovery configuration")

    discover = commands.add_parser("discover", help="Collect architecture discovery candidates")
    discover.add_argument(
        "source", choices=["github", "hacker-news", "all"], help="Source to collect from"
    )
    discover.add_argument("--limit", type=int, default=10, help="Maximum results per query")
    discover.add_argument(
        "--output-dir", type=Path, default=None,
        help="Observation directory (default: data/observations)",
    )
    discover.add_argument(
        "--dry-run", action="store_true",
        help="Fetch and validate records without writing them",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "status":
            print(f"Open Architecture Intelligence {__version__}")
            print("Discovery: GitHub repositories and Hacker News discussions available.")
            print("Scheduled execution: configured through GitHub Actions.")
        elif args.command == "validate-config":
            validate_project_configs()
            print("Configuration is valid.")
        elif args.command == "discover":
            if not 1 <= args.limit <= 100:
                raise ValueError("--limit must be between 1 and 100.")
            runners = {
                "github": run_github_discovery,
                "hacker-news": run_hacker_news_discovery,
                "all": run_all_discovery,
            }
            result = runners[args.source](
                limit=args.limit, output_dir=args.output_dir, dry_run=args.dry_run
            )
            print(json.dumps(result, indent=2))
        else:
            build_parser().print_help()
    except (
        OSError, ValueError, GitHubCollectorError, HackerNewsCollectorError
    ) as exc:
        print(f"OAI failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
