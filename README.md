# Open Architecture Intelligence

Python tools for collecting software architecture-related source data, maintaining dated observations, generating reports and preparing knowledge updates for human review.

## Repositories

- [Open Architecture Knowledge](https://github.com/Sandhiya0305/open-architecture-knowledge) - the developer-facing architecture and technology reference.

## Current capabilities

- Collect repository metadata from GitHub and public discussions from Hacker News.
- Read configured RSS and Atom feeds.
- Classify observations using a curated architecture taxonomy and validate their structure.
- Store dated observations as append-only JSON Lines.
- Generate sample-limited daily and rolling seven-day reports.
- Assess evidence and extract source-linked candidate statements from configured editorial, practitioner and research feeds.
- Record authenticated editorial review decisions and prepare draft knowledge pull requests.

GitHub and Hacker News activity are discovery signals, not evidence of architecture quality or performance. Vendor feeds can contribute discovery observations, but vendor-originated statements are not eligible for claim extraction. Publisher categories describe the source perspective; they are not numeric credibility scores and do not upgrade evidence status. Claim extraction requires architecture context and a causal, comparative or decision statement; it does not establish truth. Only extracted performance-related sentences are routed to benchmark methodology assessment; unrelated performance wording elsewhere in an article does not reclassify every statement. Missing workload, environment, versions, methodology or results remain missing, and no assessment automatically marks evidence as verified.
RSS items without a usable article summary remain discovery observations; OAI does not infer claims from titles or fetch full article pages by default. A zero-claim run is therefore possible and should not be "fixed" by relaxing evidence requirements.

## Requirements

- Python 3.11 or later
- Git
- [uv](https://docs.astral.sh/uv/) for the locked development environment
- Optional: a GitHub token for authenticated API access

## Install

```bash
uv sync --locked --extra dev
```

## Use

```bash
uv run oai status
uv run oai validate-config
uv run oai discover github --limit 10
uv run oai discover hacker-news --limit 10
uv run oai discover rss --limit 10
uv run oai discover all --limit 10 --dry-run
uv run oai report trends --period daily
uv run oai report trends --period weekly
uv run oai assess evidence
uv run oai claims review-queue
```

Set `GITHUB_TOKEN` in the environment to use the authenticated GitHub API quota. Do not commit credentials or tokens.

## Review and publishing

Review decisions require `OAI_REVIEW_TOKEN`, a GitHub token belonging to the reviewer. OAI checks the token against GitHub's authenticated-user endpoint and requires the supplied reviewer login to match the returned account. A review also requires an explicit attestation that the linked source was opened and checked:

```bash
uv run oai claims review <claim-id> \
  --decision approve \
  --reviewer <github-login> \
  --note "Source context and limitations checked." \
  --source-checked
```

The source-check field records the reviewer's attestation; it is not independent proof that the source was read. Approval is editorial approval, not technical verification.

Publishing a draft pull request to the knowledge repository uses a separate `OAI_GITHUB_TOKEN` with access to that repository. It is not interchangeable with the review token. The publisher creates a candidate page under `docs/research-candidates/`, restores the local clone's original branch and never merges the pull request.

## Data and configuration

- `config/` - source registry, taxonomy and discovery queries.
- `schema/` - versioned JSON schemas for observations, claims and review decisions.
- `src/oai_intelligence/` - collectors, pipeline, validation, reports and review tools.
- `tests/` - automated tests and representative public API/feed fixtures.
- `data/observations/` - append-only observation records.
- `data/reviews/` - append-only human review decisions.
- `reports/` - local generated reports; scheduled reports are uploaded as 30-day workflow artifacts and are not committed.

Observation records are schema-versioned. `source_record_id` identifies a source item; `observation_id` fingerprints its content and measured metadata while excluding retrieval timestamps. Repeated unchanged items are skipped, while a newly enriched or changed snapshot is appended. Older records are normalized in memory when loaded; the original append-only JSONL history is not rewritten. Trend counts describe the collected sample only and are not estimates of adoption or developer interest.

The daily GitHub Actions workflow continues with available sources when an individual collector fails. It stores observation records, uploads reports as artifacts and opens or updates a GitHub issue when a run fails. It does not automatically approve claims or merge knowledge changes.

## Development checks

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src/oai_intelligence
uv run oai validate-config
```

## Contributing

Keep changes focused, add tests for behavior changes, preserve source attribution and avoid committing secrets or local environment files. See the repository workflows for automated checks.

## License

This project is licensed under the [MIT License](LICENSE).
