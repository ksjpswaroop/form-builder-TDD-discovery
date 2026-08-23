"""Tests for discovery schema loading."""

from app.services.schema_loader import load_discovery_schema


def test_load_discovery_schema_has_sections():
    schema = load_discovery_schema()
    assert len(schema.sections) == 10
    section_ids = {s.id for s in schema.sections}
    assert "security" in section_ids
    assert "outcomes" in section_ids


def test_load_discovery_schema_has_fields():
    schema = load_discovery_schema()
    assert len(schema.fields) >= 20
    field_ids = {f.id for f in schema.fields}
    assert "SEC-THREAT-MODEL" in field_ids
    assert "OUT-PRIMARY-GOAL" in field_ids


def test_application_fields_have_applies_to():
    schema = load_discovery_schema()
    app_fields = [f for f in schema.fields if f.applies_to == "application"]
    assert len(app_fields) >= 3
