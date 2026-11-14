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
- Generate daily and rolling seven-day observation snapshots.
- Prepare evidence assessments and source-linked candidate claims.
- Record authenticated review decisions and prepare draft knowledge pull requests.

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

### Review a candidate

Review decisions require `OAI_REVIEW_TOKEN`, a GitHub token belonging to the reviewer. OAI checks the token against GitHub's authenticated-user endpoint and requires the supplied reviewer login to match the returned account. A review also requires an explicit attestation that the linked source was opened and checked:

```bash
oai claims review <claim-id> \
  --decision approve \
  --reviewer <github-login> \
  --note "Source context and limitations checked." \
  --source-checked
```

The source-check field records the reviewer's attestation; it is not independent proof that the source was read. An approval remains editorial approval, not technical verification.

Publishing a draft pull request to the knowledge repository uses a separate `OAI_GITHUB_TOKEN` with access to that repository. It is not interchangeable with the review token.

Run tests and lint checks:

```bash
python -m pytest
ruff check .
```

## Data and configuration

- `config/` — source registry, taxonomy and discovery queries.
- `schema/` — versioned JSON schemas for observations, claims and review decisions.
- `src/oai_intelligence/` — collectors, pipeline, validation, reports and review tools.
- `tests/` — automated tests.
- `data/observations/` — append-only observation records.
- `data/reviews/` — append-only human review decisions.
- `reports/` — generated discovery, evidence and claim reports.

Observation records are schema-versioned. Older records are normalized in memory when loaded; the original append-only JSONL history is not rewritten.

The daily GitHub Actions workflow runs discovery and report generation. It continues with available sources when an individual collector fails and reports partial failures. It does not automatically approve claims or merge knowledge changes. Cross-repository draft pull requests require the documented repository secret and variable configuration in the workflow.

## Contributing

Keep changes focused, add tests for behavior changes, preserve source attribution and avoid committing secrets or local environment files. See the repository workflows for automated checks.

## License

This project is licensed under the [MIT License](LICENSE).
