import pytest
from jsonschema.exceptions import ValidationError

from oai_intelligence.validation import validate_observation

VALID_OBSERVATION = {
    "observation_id": "test-001",
    "source": {"url": "https://example.com/architecture", "source_type": "article"},
    "observed_at": "2026-11-13T09:00:00+05:30",
    "category": "modular-monolith",
    "ecosystem": "python",
    "claim": "The article describes explicit module boundaries.",
    "claim_type": "architecture_description",
    "evidence_status": "unverified",
    "tags": ["modules", "boundaries"],
}


def test_valid_observation_passes_schema() -> None:
    validate_observation(VALID_OBSERVATION)


def test_invalid_timestamp_is_rejected() -> None:
    observation = {**VALID_OBSERVATION, "observed_at": "yesterday"}
    with pytest.raises(ValidationError):
        validate_observation(observation)


def test_performance_claim_can_remain_unverified_without_benchmark() -> None:
    observation = {
        **VALID_OBSERVATION,
        "claim_type": "performance_claim",
        "evidence_status": "unverified",
    }
    validate_observation(observation)
