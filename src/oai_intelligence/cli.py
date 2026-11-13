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
from oai_intelligence.publishing import PublishingError, publish_knowledge_candidates
from oai_intelligence.reports import generate_trend_report
from oai_intelligence.review import prepare_knowledge_candidates, record_claim_review
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

    claims = commands.add_parser("claims", help="Extract and review candidate claims")
    claim_commands = claims.add_subparsers(dest="claims_command")
    queue = claim_commands.add_parser("review-queue", help="Generate the source-linked claim queue")
    queue.add_argument("--as-of", type=date.fromisoformat, default=None)
    queue.add_argument("--data-dir", type=Path, default=None)
    queue.add_argument("--output-dir", type=Path, default=None)
    queue.add_argument("--reviews-file", type=Path, default=None)
    review = claim_commands.add_parser("review", help="Record a human claim review decision")
    review.add_argument("claim_id")
    review.add_argument("--decision", choices=["approve", "reject", "needs-evidence"], required=True)
    review.add_argument("--reviewer", required=True)
    review.add_argument("--note", required=True)
    review.add_argument("--as-of", type=date.fromisoformat, default=None)
    review.add_argument("--queue-dir", type=Path, default=None)
    review.add_argument("--reviews-file", type=Path, default=None)
    prepare = claim_commands.add_parser("prepare-knowledge", help="Prepare approved claims for knowledge review")
    prepare.add_argument("--as-of", type=date.fromisoformat, default=None)
    prepare.add_argument("--queue-dir", type=Path, default=None)
    prepare.add_argument("--reviews-file", type=Path, default=None)
    prepare.add_argument("--output-dir", type=Path, default=None)

    publish = commands.add_parser("publish", help="Publish reviewed knowledge candidates as a pull request")
    publish.add_argument("publish_target", choices=["knowledge"])
    publish.add_argument("--bundle", type=Path, required=True)
    publish.add_argument("--repo-path", type=Path, required=True)
    publish.add_argument("--base", default="main")
    publish.add_argument("--as-of", type=date.fromisoformat, default=None)

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
            print("Analysis: trend reports, evidence assessments, and source-linked claim review.")
            print("Publishing: human-approved candidates are proposed through draft pull requests only.")
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
                data_dir=args.data_dir, output_dir=args.output_dir, as_of=args.as_of,
                reviews_file=args.reviews_file,
            )
            print(json.dumps(result, indent=2))
        elif args.command == "claims" and args.claims_command == "review":
            result = record_claim_review(
                claim_id=args.claim_id, decision=args.decision, reviewer=args.reviewer,
                note=args.note, queue_dir=args.queue_dir, reviews_file=args.reviews_file,
                as_of=args.as_of,
            )
            print(json.dumps(result, indent=2))
        elif args.command == "claims" and args.claims_command == "prepare-knowledge":
            result = prepare_knowledge_candidates(
                queue_dir=args.queue_dir, reviews_file=args.reviews_file,
                output_dir=args.output_dir, as_of=args.as_of,
            )
            print(json.dumps(result, indent=2))
        elif args.command == "publish" and args.publish_target == "knowledge":
            result = publish_knowledge_candidates(
                bundle_path=args.bundle, repo_path=args.repo_path,
                base_branch=args.base, as_of=args.as_of,
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
        PublishingError,
    ) as exc:
        print(f"OAI failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
