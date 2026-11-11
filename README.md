# Open Architecture Intelligence

An evidence-first, open-source research engine that discovers software architecture developments, evaluates claims, tracks signals over time, and proposes reviewed updates to the companion [Open Architecture Knowledge](https://github.com/Sandhiya0305/open-architecture-knowledge) repository.

## Scope
Initial ecosystems: **Node.js, Python, Java, and PHP**.

Initial architecture taxonomy:
- Layered Architecture
- Modular Monolith
- Microservices
- Clean Architecture
- Event-Driven Architecture

## Operating principles
1. Evidence before conclusions: preserve source URLs, publication dates, and claim provenance.
2. Popularity is not performance: adoption and mention counts are separate from measured performance.
3. No invented benchmarks: performance claims require workload, environment, versions, methodology, and results.
4. AI assists; validation decides: deterministic code validates schemas and calculations.
5. Human review is mandatory: generated knowledge is proposed through pull requests, never silently merged.
6. Respect source terms, robots directives, licenses, and rate limits. Prefer metadata and links over republishing source text.

## Planned pipeline
- Discover: GitHub, Hacker News, RSS, and selected public sources.
- Extract: architecture styles, technologies, decisions, claims, limitations, and evidence.
- Normalize: vocabulary, aliases, deduplication, and source metadata.
- Classify and verify: architecture vs framework, novelty, evidence quality, and claim status.
- Analyze: time-series signals and verified benchmark records.
- Generate: documentation and reviewable knowledge updates.
- Validate and propose: schema/tests/link checks followed by a pull request.

## Repository map
- `src/oai_intelligence/`: Python engine.
- `config/`: source registry and architecture taxonomy.
- `schemas/`: machine-readable data contracts.
- `tests/`: automated tests.
- `.github/workflows/`: continuous integration.

## Development
Requires Python 3.11 or newer.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
python -m oai_intelligence --help
```

## Status
Foundational scaffold. Collection, extraction, verification, trend analysis, and publishing will be implemented incrementally. No performance ranking is claimed by this repository at this stage.

## Companion repository
The curated knowledge base lives at [open-architecture-knowledge](https://github.com/Sandhiya0305/open-architecture-knowledge).
