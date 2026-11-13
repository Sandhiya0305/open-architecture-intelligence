"""Command-line interface for Open Architecture Intelligence."""

import argparse
import json
import sys
from pathlib import Path

from oai_intelligence import __version__
from oai_intelligence.collectors.github import GitHubCollectorError
from oai_intelligence.pipeline import run_github_discovery
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
    discover.add_argument("source", choices=["github"], help="Source to collect from")
    discover.add_argument("--limit", type=int, default=10, help="Maximum results per ecosystem")
    discover.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Observation directory (default: data/observations)",
    )
    discover.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and validate records without writing them",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "status":
            print(f"Open Architecture Intelligence {__version__}")
            print("Discovery: GitHub repository metadata collector available.")
            print("Next sources: Hacker News and curated RSS.")
        elif args.command == "validate-config":
            validate_project_configs()
            print("Configuration is valid.")
        elif args.command == "discover":
            if not 1 <= args.limit <= 100:
                raise ValueError("--limit must be between 1 and 100.")
            result = run_github_discovery(
                limit=args.limit,
                output_dir=args.output_dir,
                dry_run=args.dry_run,
            )
            print(json.dumps(result, indent=2))
        else:
            build_parser().print_help()
    except (OSError, ValueError, GitHubCollectorError) as exc:
        print(f"OAI failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
