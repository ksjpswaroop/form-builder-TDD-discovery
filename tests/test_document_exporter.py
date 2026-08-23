"""Tests for document export."""

import json
from pathlib import Path

from app.services.assessment_plan import generate_plan_yaml
from app.services.document_exporter import export_all
from app.services.session_service import create_session, save_session_state


def test_export_all_creates_files(db_session, sample_state, tmp_path):
    record, state = create_session(db_session)
    state.company = sample_state.company
    state.objectives = sample_state.objectives
    state.applications = sample_state.applications
    state.plan_yaml = generate_plan_yaml(state)
    save_session_state(db_session, record, state)

    docs_root = tmp_path / "documents"
    result = export_all(record, state, documents_root=docs_root)

    out_dir = docs_root / str(record.id)
    json_file = out_dir / f"{result.stem}.json"
    assert json_file.exists()
    assert (out_dir / f"{result.stem}.pdf").exists()
    assert (out_dir / f"{result.stem}.xlsx").exists()

    with open(json_file, encoding="utf-8") as f:
        payload = json.load(f)
    assert payload["company_name"] == "Acme Corp"
    assert payload["products"] == "Payments platform"
    assert payload["access_key"] == record.access_key
