"""Command-line interface for Open Architecture Intelligence."""

import argparse
import sys
from pathlib import Path

from jsonschema.exceptions import ValidationError

from oai_intelligence import __version__
from oai_intelligence.validation import validate_observation_file, validate_project_configs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="oai", description="Evidence-first software architecture intelligence."
    )
    parser.add_argument("--version", action="version", version=f"OAI {__version__}")
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("status", help="Show project foundation status")
    commands.add_parser("validate-config", help="Validate source and architecture YAML")
    observation = commands.add_parser(
        "validate-observation", help="Validate one observation JSON file"
    )
    observation.add_argument("path", type=Path, help="Path to an observation JSON file")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "status":
            print(f"Open Architecture Intelligence {__version__}")
            print("Foundation: configuration and observation validation available.")
            print("Discovery collectors and trend analysis are not implemented yet.")
        elif args.command == "validate-config":
            validate_project_configs()
            print("Configuration is valid.")
        elif args.command == "validate-observation":
            validate_observation_file(args.path)
            print(f"Valid observation: {args.path}")
        else:
            build_parser().print_help()
    except (OSError, ValueError, TypeError, ValidationError) as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
