"""Command-line entry point for Open Architecture Intelligence."""

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="oai",
        description="Evidence-first software architecture intelligence.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="Open Architecture Intelligence 0.1.0",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("status", help="Show the current scaffold status")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "status":
        print("OAI scaffold is installed. Discovery pipeline is not implemented yet.")
    else:
        build_parser().print_help()


if __name__ == "__main__":
    main()
