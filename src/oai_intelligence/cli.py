"""Command-line interface for Open Architecture Intelligence."""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from oai_intelligence import __version__
from oai_intelligence.assess import generate_evidence_assessment
from oai_intelligence.claims import generate_claim_review_queue
from oai_intelligence.collectors.github import GitHubCollectorError
from oai_intelligence.collectors.hacker_news import HackerNewsCollectorError
from oai_intelligence.collectors.rss import RSSCollectorError
from oai_intelligence.pipeline import (
    run_all_discovery,
    run_github_discovery,
    run_hacker_news_discovery,
    run_rss_discovery,
)
from oai_intelligence.reports import generate_trend_report
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
        "source",
        choices=["github", "hacker-news", "rss", "all"],
        help="Source to collect from",
    )
    discover.add_argument("--limit", type=int, default=10, help="Maximum results per query/feed")
    discover.add_argument("--output-dir", type=Path, default=None)
    discover.add_argument("--dry-run", action="store_true")

    report = commands.add_parser("report", help="Generate reports")
    report_commands = report.add_subparsers(dest="report_command")
    trends = report_commands.add_parser("trends", help="Generate daily or weekly trend reports")
    trends.add_argument("--period", choices=["daily", "weekly"], default="daily")
    trends.add_argument("--as-of", type=date.fromisoformat, default=None)
    trends.add_argument("--data-dir", type=Path, default=None)
    trends.add_argument("--output-dir", type=Path, default=None)

    claims = commands.add_parser("claims", help="Extract candidate claims for human review")
    claims.add_argument("claims_command", choices=["review-queue"])
    claims.add_argument("--as-of", type=date.fromisoformat, default=None)
    claims.add_argument("--data-dir", type=Path, default=None)
    claims.add_argument("--output-dir", type=Path, default=None)

    assess = commands.add_parser("assess", help="Assess evidence without changing observations")
    assess_commands = assess.add_subparsers(dest="assess_command")
    evidence = assess_commands.add_parser("evidence", help="Generate per-observation assessments")
    evidence.add_argument("--as-of", type=date.fromisoformat, default=None)
    evidence.add_argument("--data-dir", type=Path, default=None)
    evidence.add_argument("--output-dir", type=Path, default=None)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "status":
            print(f"Open Architecture Intelligence {__version__}")
            print("Discovery: GitHub repositories, Hacker News discussions, and RSS/Atom articles.")
            print("Analysis: deterministic trend reports and conservative evidence assessments.")
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
                "rss": run_rss_discovery,
                "all": run_all_discovery,
            }
            result = runners[args.source](
                limit=args.limit, output_dir=args.output_dir, dry_run=args.dry_run
            )
            print(json.dumps(result, indent=2))
        elif args.command == "report" and args.report_command == "trends":
            result = generate_trend_report(
                period=args.period,
                as_of=args.as_of,
                data_dir=args.data_dir,
                output_dir=args.output_dir,
            )
            print(json.dumps(result, indent=2))
        elif args.command == "claims" and args.claims_command == "review-queue":
            result = generate_claim_review_queue(
                data_dir=args.data_dir, output_dir=args.output_dir, as_of=args.as_of
            )
            print(json.dumps(result, indent=2))
        elif args.command == "assess" and args.assess_command == "evidence":
            result = generate_evidence_assessment(
                data_dir=args.data_dir,
                output_dir=args.output_dir,
                as_of=args.as_of,
            )
            print(json.dumps(result, indent=2))
        else:
            build_parser().print_help()
    except (
        OSError,
        ValueError,
        TypeError,
        GitHubCollectorError,
        HackerNewsCollectorError,
        RSSCollectorError,
    ) as exc:
        print(f"OAI failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
