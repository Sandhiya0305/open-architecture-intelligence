# Open Architecture Intelligence

An evidence-first research engine that discovers software architecture signals, preserves source provenance, evaluates claims, tracks history, and proposes reviewed updates to the companion [Open Architecture Knowledge](https://github.com/Sandhiya0305/open-architecture-knowledge) repository.

## Initial scope

- Ecosystems: Node.js, Python, Java, and PHP.
- Architecture taxonomy: Layered Architecture, Modular Monolith, Microservices, Clean Architecture, and Event-Driven Architecture.
- Sources: GitHub repository metadata and Hacker News discussions. Curated RSS is planned but remains disabled until a reviewed feed list is configured.

## Evidence principles

- Repository mentions and popularity metrics are discovery signals, not proof of architecture adoption or performance.
- Keep stars, forks, releases, points, and discussion activity separate from benchmark measurements.
- Performance claims require workload, environment, hardware, versions, methodology, results, measurement date, and source.
- Missing methodology means unverified; never invent comparisons.
- Preserve source URLs and dates. Do not republish full third-party articles.
- Generated knowledge updates require human review through pull requests; no automatic merge.

## Install and run

    python -m venv .venv
    # Windows: .venv\Scripts\activate
    python -m pip install -e ".[dev]"

    oai status
    oai validate-config
    oai discover github --limit 10
    oai discover hacker-news --limit 10
    oai discover all --limit 10
    oai discover all --limit 5 --dry-run

Set GITHUB_TOKEN in your environment to use an authenticated GitHub API quota. Never commit tokens or secrets.

Hacker News full-text discovery uses the public Algolia Hacker News Search API at https://hn.algolia.com/api/v1, not the Firebase item API. Story points and comment counts are stored only as discussion metadata.

## Scheduled execution

The daily-discovery workflow runs the combined GitHub and Hacker News discovery pipeline every day at 00:30 UTC (06:00 India Standard Time). It can also be started manually from the repository Actions tab. New dated JSONL observations are committed to this repository. GitHub-hosted runners mean your personal computer does not need to stay on.

GitHub Actions schedules can be delayed and may be disabled for inactive repositories. Use the manual workflow trigger when needed and check the Actions tab for run results.

## Data layout

- config/: source registry, architecture taxonomy, and discovery queries.
- src/oai_intelligence/collectors/: source-specific collectors.
- data/observations/YYYY-MM-DD.jsonl: append-only daily observation snapshots.
- schema/: validated observation contract.
- tests/: mocked API and deterministic unit tests.

The JSONL history is the durable record. Local SQLite indexing, RSS discovery, trend analysis, and knowledge-repository pull-request publishing remain future milestones.
