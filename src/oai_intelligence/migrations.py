"""Compatibility migrations for append-only observation records."""

from copy import deepcopy
from typing import Any

CURRENT_OBSERVATION_SCHEMA_VERSION = 1


def migrate_observation_record(record: dict[str, Any]) -> dict[str, Any]:
    """Return a normalized copy of a legacy or current observation record."""
    migrated = deepcopy(record)
    version = migrated.get("schema_version", 0)
    if version == 0:
        migrated["schema_version"] = 1
        source = migrated.get("source")
        if isinstance(source, dict):
            source.setdefault("content_excerpt", "")
    elif version != CURRENT_OBSERVATION_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported observation schema version {version!r}; "
            f"this version supports up to {CURRENT_OBSERVATION_SCHEMA_VERSION}."
        )
    return migrated
