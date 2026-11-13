# Open Architecture Intelligence

An evidence-first research engine that discovers software architecture signals, preserves source provenance, evaluates claims, tracks history, and proposes reviewed updates to the companion [Open Architecture Knowledge](https://github.com/Sandhiya0305/open-architecture-knowledge) repository.

## Initial scope

- Ecosystems: Node.js, Python, Java, and PHP.
- Architecture taxonomy: Layered Architecture, Modular Monolith, Microservices, Clean Architecture, and Event-Driven Architecture.
- Initial sources: GitHub repository metadata, Hacker News discussions, and curated RSS feeds.

## Evidence principles

- Repository mentions and popularity metrics are discovery signals, not proof of architecture adoption or performance.
- Keep stars, forks, releases, and discussion activity separate from benchmark measurements.
- Performance claims require workload, environment, hardware, versions, methodology, results, measurement date, and source.
- Missing methodology means unverified; never invent comparisons.
- Preserve source URLs and dates. Do not republish full third-party articles.
- Generated knowledge updates require human review through pull requests; no automatic merge.

## Current implementation

The first working vertical slice discovers GitHub repositories matching architecture-related terms across the four initial ecosystems. It classifies repository metadata as a discovery candidate, validates each record, and appends it to a dated JSONL history file.

    python -m venv .venv
    # Windows: .venv\Scripts\activate
    python -m pip install -e ".[dev]"

    oai status
    oai validate-config
    oai discover github --limit 10
    oai discover github --limit 5 --dry-run

Set GITHUB_TOKEN in your environment to use an authenticated GitHub API quota. Never commit tokens or secrets.

## Data layout

- config/: source registry, architecture taxonomy, and discovery queries.
- src/oai_intelligence/collectors/: source-specific collectors.
- data/observations/YYYY-MM-DD.jsonl: append-only daily observation snapshots.
- schema/: validated observation contract.
- tests/: mocked API and deterministic unit tests.

The JSONL history is the durable record. Local SQLite indexing and richer trend analysis will be added in later phases.

## Development status

GitHub repository discovery is the first implemented source. Hacker News, RSS, release-level collection, corroboration, trend analysis, and knowledge-repository pull-request publishing are subsequent milestones.
