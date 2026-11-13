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

## Human review and knowledge publishing

The review process is deliberately separate from extraction. First generate the claim queue and inspect its Markdown/JSON output. Copy a claim ID from the report and record a decision:

    oai claims review <CLAIM_ID> --decision approve --reviewer "Your Name" --note "Checked the original source and context."
    oai claims review <CLAIM_ID> --decision needs-evidence --reviewer "Your Name" --note "The source does not describe the workload."
    oai claims review <CLAIM_ID> --decision reject --reviewer "Your Name" --note "The sentence is not a technical architecture claim."

Decisions are appended to data/reviews/claim-decisions.jsonl. A later decision supersedes the earlier decision for preparation, while the history remains intact. Commit and push this file so scheduled GitHub Actions runs can see the decisions. Do not put secrets or private information in reviewer notes; the repository is public.

Prepare a knowledge candidate bundle containing only currently approved claims:

    oai claims prepare-knowledge --as-of 2026-11-13

The generated Markdown remains explicitly **UNVERIFIED**. Editorial approval only means a human considers the candidate relevant and source-linked; it does not establish truth, causality, reproducibility, or performance. Rejected and needs-evidence claims are excluded.

To open a draft pull request in the companion knowledge repository, make sure its local clone is clean and authenticated for Git push. Set OAI_GITHUB_TOKEN to a fine-grained GitHub token with **Contents: Read and write** and **Pull requests: Read and write** access limited to `Sandhiya0305/open-architecture-knowledge`, then run:

    oai publish knowledge --bundle reports/knowledge-candidates/2026-11-13.md --repo-path ../open-architecture-knowledge --as-of 2026-11-13

The publisher checks the exact repository remote, refuses dirty working trees and overwrites, creates a dedicated branch, pushes the candidate file under evidence/candidates/, and opens a **draft** pull request. It never writes directly to the knowledge repository's default branch or merges a pull request. The Git credential manager must also be authenticated for the push; the API token is read from the environment and is never written to source files.

For an optional GitHub Actions hand-off, add a repository secret named `OAI_KNOWLEDGE_TOKEN` with the same narrowly scoped permissions, and a repository variable named `OAI_ENABLE_KNOWLEDGE_PR` set to `true`. Then use **Actions -> Daily Architecture Discovery -> Run workflow**. Only manual runs attempt the cross-repository draft PR; scheduled runs never publish to the knowledge repository. If there are no approved candidates, the PR step is skipped. Without both settings, discovery and report generation continue normally.

## Scheduled execution

The daily-discovery workflow runs the GitHub, Hacker News, and RSS/Atom discovery pipeline every day at 00:30 UTC (06:00 India Standard Time), then generates daily and rolling weekly reports, evidence assessments, a claim review queue, and a knowledge-candidate bundle based only on previously recorded human approvals. It can also be started manually from the repository Actions tab. New dated JSONL observations and reports are committed to this repository. GitHub-hosted runners mean your personal computer does not need to stay on.

GitHub Actions schedules can be delayed and may be disabled for inactive repositories. Use the manual workflow trigger when needed and check the Actions tab for run results.

## Data layout

- config/: source registry, architecture taxonomy, and discovery queries.
- src/oai_intelligence/collectors/: source-specific collectors.
- data/observations/YYYY-MM-DD.jsonl: append-only daily observation snapshots.
- reports/daily/ and reports/weekly/: generated Markdown and JSON trend snapshots.
- reports/evidence/: per-observation evidence assessments and summary reports.
- reports/claims/: source-linked candidate claims awaiting human review.
- reports/knowledge-candidates/: Markdown bundles containing only human-approved but still unverified candidates.
- data/reviews/: append-only human review decisions; never store secrets or personal data here.
- schema/: validated observation, claim-candidate, and human-review contracts.
- tests/: mocked API and deterministic unit tests.

The JSONL history is the durable record. Evidence assessments are separate review aids, not edits to historical observations. Local SQLite indexing, stronger claim-level corroboration, and knowledge-repository pull-request publishing remain future milestones.
