# Open Architecture Intelligence

An evidence-first research engine that discovers software architecture signals, preserves source provenance, evaluates claims, tracks history, and proposes reviewed updates to the companion [Open Architecture Knowledge](https://github.com/Sandhiya0305/open-architecture-knowledge) repository.

## Initial scope

- Ecosystems: Node.js, Python, Java, and PHP.
- Architecture taxonomy: Layered Architecture, Modular Monolith, Microservices, Clean Architecture, and Event-Driven Architecture.
- Sources: GitHub repository metadata, Hacker News discussions, and curated RSS/Atom engineering publications.

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
    oai discover rss --limit 10
    oai discover all --limit 10
    oai discover all --limit 5 --dry-run

Set GITHUB_TOKEN in your environment to use an authenticated GitHub API quota. Never commit tokens or secrets.

Hacker News full-text discovery uses the public Algolia Hacker News Search API at https://hn.algolia.com/api/v1, not the Firebase item API. Story points and comment counts are stored only as discussion metadata.

RSS/Atom discovery uses configured feeds from InfoQ Architecture & Design, AWS Architecture Blog, and Martin Fowler. Article titles, bounded feed summaries (up to 4,000 characters), canonical links, authors, and publication dates are processed; full article text is not stored or republished.

## Trend reports

Generate deterministic daily and rolling seven-day reports from the saved observation history:

    oai report trends --period daily
    oai report trends --period weekly
    oai report trends --period daily --as-of 2026-11-13

Each run writes a Markdown report and a JSON data file under reports/daily/ or reports/weekly/. Reports compare the selected window with the preceding window of equal length and summarize architecture mentions, sources, ecosystems, and evidence statuses.

These counts describe the collected discovery sample. They are not estimates of market adoption, architecture quality, or performance. A performance conclusion requires independently reviewed benchmark evidence and methodology; this report generator does not infer one.

## Evidence assessment

Generate conservative per-observation assessments:

    oai assess evidence
    oai assess evidence --as-of 2026-11-13

Outputs are stored separately under reports/evidence/ as JSONL assessments plus JSON and Markdown summaries. The assessment engine:

- Keeps original observation records unchanged.
- Separates source-activity metadata (stars, forks, discussion points/comments) from technical evidence.
- Flags exact claim matches on different publisher domains as corroboration leads, not proof.
- Checks whether performance claims include workload, environment, hardware, software versions, methodology, results, measurement date, and source URL.
- Marks complete benchmark records as ready for human review only; it does not validate experimental quality or reproducibility.
- Never automatically upgrades evidence status, approves claims, or publishes knowledge updates.

The optional evidence_details object in the observation schema holds structured benchmark details when reviewers or future extractors provide them. Empty or missing fields remain incomplete.

## Claim extraction and review queue

Generate conservative candidate claims from captured source excerpts:

    oai claims review-queue
    oai claims review-queue --as-of 2026-11-13

Outputs are written under reports/claims/ as JSONL, JSON, and Markdown. The deterministic extractor looks for explicit sentences describing decisions, benefits, or limitations. Each candidate retains its observation ID, source URL, title, architecture labels, and extraction method. Exact normalized repeats are flagged for duplicate review; a small set of opposing outcome phrases can be flagged as possible conflicts.

These are review candidates, not verified findings. The extractor does not infer claims from stars, points, titles alone, or missing source text. Older observations without captured excerpts will produce no claims. Reviewers must open the source, check context and methodology, and decide whether a claim belongs in the knowledge base. No automatic approval or publication occurs.

## Scheduled execution

The daily-discovery workflow runs the GitHub, Hacker News, and RSS/Atom discovery pipeline every day at 00:30 UTC (06:00 India Standard Time), then generates daily and rolling weekly reports, evidence assessments, and a claim review queue. It can also be started manually from the repository Actions tab. New dated JSONL observations and reports are committed to this repository. GitHub-hosted runners mean your personal computer does not need to stay on.

GitHub Actions schedules can be delayed and may be disabled for inactive repositories. Use the manual workflow trigger when needed and check the Actions tab for run results.

## Data layout

- config/: source registry, architecture taxonomy, and discovery queries.
- src/oai_intelligence/collectors/: source-specific collectors.
- data/observations/YYYY-MM-DD.jsonl: append-only daily observation snapshots.
- reports/daily/ and reports/weekly/: generated Markdown and JSON trend snapshots.
- reports/evidence/: per-observation evidence assessments and summary reports.
- reports/claims/: source-linked candidate claims awaiting human review.
- schema/: validated observation contract, including optional structured benchmark details.
- tests/: mocked API and deterministic unit tests.

The JSONL history is the durable record. Evidence assessments are separate review aids, not edits to historical observations. Local SQLite indexing, stronger claim-level corroboration, and knowledge-repository pull-request publishing remain future milestones.
