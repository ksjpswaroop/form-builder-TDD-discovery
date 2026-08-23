"""Load and validate the deterministic discovery schema."""

from pathlib import Path

import yaml

from app.config import SCHEMA_PATH
from app.schemas import DiscoverySchema, SchemaField, SchemaSection


def load_discovery_schema(path: Path | None = None) -> DiscoverySchema:
    schema_path = path or SCHEMA_PATH
    with open(schema_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    sections = [SchemaSection(**s) for s in raw.get("sections", [])]
    fields = [SchemaField(**f) for f in raw.get("fields", [])]
    return DiscoverySchema(sections=sections, fields=fields)


def get_section_by_id(schema: DiscoverySchema, section_id: str) -> SchemaSection | None:
    for section in schema.sections:
        if section.id == section_id:
            return section
    return None


def get_field_by_id(schema: DiscoverySchema, field_id: str) -> SchemaField | None:
    for field in schema.fields:
        if field.id == field_id:
            return field
    return None


def get_applicable_fields(
    schema: DiscoverySchema,
    answered_ids: set[str],
    application_names: list[str] | None = None,
) -> list[SchemaField]:
    """Return schema fields not yet answered."""
    applicable: list[SchemaField] = []
    for field in schema.fields:
        if field.id in answered_ids:
            continue
        if field.applies_to == "application" and not application_names:
            continue
        applicable.append(field)
    return applicable
