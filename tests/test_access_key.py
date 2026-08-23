"""Tests for access key generation and lookup."""

from app.services.session_service import create_session, load_session_by_access_key


def test_access_key_generated_on_create(db_session):
    record, _ = create_session(db_session)
    assert record.access_key
    assert len(record.access_key) >= 32


def test_access_keys_are_unique(db_session):
    r1, _ = create_session(db_session)
    r2, _ = create_session(db_session)
    assert r1.access_key != r2.access_key


def test_load_by_access_key(db_session, sample_state):
    record, state = create_session(db_session)
    state.company.company_name = "Key Test Co"
    from app.services.session_service import save_session_state

    save_session_state(db_session, record, sample_state)

    loaded_record, loaded_state = load_session_by_access_key(db_session, record.access_key)
    assert loaded_record.id == record.id
    assert loaded_state.company.company_name == sample_state.company.company_name
