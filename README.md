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

## Current capabilities

- Load and validate the source registry and architecture taxonomy.
- Validate observation records against the JSON Schema contract, including date/time and URI formats.
- Run locally through the oai command-line interface.
- Exercise the package, validators, and example record in continuous integration.

Discovery collectors, extraction, evidence corroboration, historical storage, trend analysis, and pull-request publishing remain future phases. No performance ranking is claimed at this stage.

## Repository map

- src/oai_intelligence/: Python engine and CLI.
- config/: source registry and architecture taxonomy.
- schema/: machine-readable observation contract.
- examples/observations/: synthetic validation fixture (not factual research).
- tests/: automated tests.
- .github/workflows/: continuous integration.

## Development

Requires Python 3.11 or newer.

    python -m venv .venv
    # Windows: .venv\Scripts\activate
    # macOS/Linux: source .venv/bin/activate
    python -m pip install -e ".[dev]"
    pytest
    oai status
    oai validate-config
    oai validate-observation examples/observations/example.json

## Companion repository

The curated knowledge base lives at [open-architecture-knowledge](https://github.com/Sandhiya0305/open-architecture-knowledge).
