# Open Architecture Intelligence

Python tools for collecting software architecture-related source data, maintaining dated observations, generating reports and preparing knowledge updates for human review.

## Repositories

- [Open Architecture Knowledge](https://github.com/Sandhiya0305/open-architecture-knowledge) — the developer-facing architecture and technology reference.

## Current capabilities

- Collect repository metadata from GitHub.
- Collect public discussions from Hacker News.
- Read configured RSS and Atom feeds.
- Classify observations using the project taxonomy and validate their structure.
- Store dated observations as JSON Lines.
- Generate daily and weekly discovery reports.
- Prepare evidence assessments and source-linked candidate claims.
- Record review decisions and prepare draft knowledge pull requests.

Collected activity and candidate claims are not proof of adoption, quality or performance. Knowledge updates require human review.

## Requirements

- Python 3.11 or later
- Git
- Optional: a GitHub token for authenticated API access

## Install

Create and activate a virtual environment, then install the project:

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

python -m pip install -e ".[dev]"
```

## Use

```bash
oai status
oai validate-config

oai discover github --limit 10
oai discover hacker-news --limit 10
oai discover rss --limit 10
oai discover all --limit 10 --dry-run

oai report trends --period daily
oai report trends --period weekly
oai assess evidence
oai claims review-queue
```

Set `GITHUB_TOKEN` in the environment to use the authenticated GitHub API quota. Do not commit credentials or tokens.

Run tests and lint checks:

```bash
python -m pytest
ruff check .
```

## Data and configuration

- `config/` — source registry, taxonomy and discovery queries.
- `schema/` — JSON schemas for observations, claims and review decisions.
- `src/oai_intelligence/` — collectors, pipeline, validation, reports and review tools.
- `tests/` — automated tests.
- `data/observations/` — dated observation records.
- `data/reviews/` — human review decisions.
- `reports/` — generated discovery, evidence and claim reports.

The daily GitHub Actions workflow runs discovery and report generation. It does not automatically approve claims or merge knowledge changes. Cross-repository draft pull requests require the documented repository secret and variable configuration in the workflow.

## Contributing

Keep changes focused, add tests for behavior changes, preserve source attribution and avoid committing secrets or local environment files. See the repository workflows for automated checks.

## License

This project is licensed under the [MIT License](LICENSE).
