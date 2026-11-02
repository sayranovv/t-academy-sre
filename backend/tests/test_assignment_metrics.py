from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import IntegrityError, OperationalError

from app import schemas, services


@pytest.mark.parametrize("stage", ["query", "commit"])
def test_issue_counts_technical_failure_once(monkeypatch, stage):
    db = MagicMock()
    failure = OperationalError("", {}, RuntimeError("database unavailable"))
    if stage == "query":
        db.scalar.side_effect = failure
    else:
        record = MagicMock(is_active=True, operational_state="usable")
        monkeypatch.setattr(services, "require", lambda *args, **kwargs: record)
        monkeypatch.setattr(services, "has_assignments", lambda *args, **kwargs: False)
        monkeypatch.setattr(services, "read_record", lambda *args: object())
        db.begin.return_value.__exit__.side_effect = failure
    successes = services.EQUIPMENT_ASSIGNMENTS._value.get()
    failures = services.EQUIPMENT_ASSIGNMENTS_FAILS._value.get()

    with pytest.raises(OperationalError) as caught:
        services.issue(db, schemas.AssignmentCreate(employee_id=1, equipment_id=1))

    assert caught.value is failure
    assert services.EQUIPMENT_ASSIGNMENTS._value.get() == successes
    assert services.EQUIPMENT_ASSIGNMENTS_FAILS._value.get() == failures + 1


@pytest.mark.parametrize(
    "failure",
    [
        services.DomainError("equipment_already_assigned", "Оборудование уже выдано"),
        IntegrityError("", {}, RuntimeError("constraint conflict")),
    ],
)
def test_issue_excludes_expected_rejections(failure):
    db = MagicMock()
    db.scalar.side_effect = failure
    successes = services.EQUIPMENT_ASSIGNMENTS._value.get()
    failures = services.EQUIPMENT_ASSIGNMENTS_FAILS._value.get()

    with pytest.raises(type(failure)) as caught:
        services.issue(db, schemas.AssignmentCreate(employee_id=1, equipment_id=1))

    assert caught.value is failure
    assert services.EQUIPMENT_ASSIGNMENTS._value.get() == successes
    assert services.EQUIPMENT_ASSIGNMENTS_FAILS._value.get() == failures


@pytest.mark.parametrize("stage", ["query", "commit"])
def test_return_counts_technical_failure_once(monkeypatch, stage):
    db = MagicMock()
    failure = OperationalError("", {}, RuntimeError("database unavailable"))
    if stage == "query":
        db.scalar.side_effect = failure
    else:
        now = datetime.now(UTC)
        assignment = MagicMock(returned_at=None, issued_at=now)
        monkeypatch.setattr(services, "require", lambda *args, **kwargs: assignment)
        monkeypatch.setattr(services, "read_record", lambda *args: object())
        db.scalar.return_value = now
        db.begin.return_value.__exit__.side_effect = failure
    successes = services.EQUIPMENT_RETURNS._value.get()
    failures = services.EQUIPMENT_RETURNS_FAILS._value.get()

    with pytest.raises(OperationalError) as caught:
        services.return_equipment(db, 1, schemas.ReturnInput())

    assert caught.value is failure
    assert services.EQUIPMENT_RETURNS._value.get() == successes
    assert services.EQUIPMENT_RETURNS_FAILS._value.get() == failures + 1


@pytest.mark.parametrize(
    "failure",
    [
        services.DomainError("not_found", "Запись не найдена", 404),
        IntegrityError("", {}, RuntimeError("constraint conflict")),
    ],
)
def test_return_excludes_expected_rejections(failure):
    db = MagicMock()
    db.scalar.side_effect = failure
    successes = services.EQUIPMENT_RETURNS._value.get()
    failures = services.EQUIPMENT_RETURNS_FAILS._value.get()

    with pytest.raises(type(failure)) as caught:
        services.return_equipment(db, 1, schemas.ReturnInput())

    assert caught.value is failure
    assert services.EQUIPMENT_RETURNS._value.get() == successes
    assert services.EQUIPMENT_RETURNS_FAILS._value.get() == failures


@pytest.mark.parametrize("already_returned", [False, True])
def test_return_counts_only_new_committed_return(monkeypatch, already_returned):
    db = MagicMock()
    now = datetime.now(UTC)
    assignment = MagicMock(issued_at=now, returned_at=now if already_returned else None)
    monkeypatch.setattr(services, "require", lambda *args, **kwargs: assignment)
    result = object()
    monkeypatch.setattr(services, "read_record", lambda *args: result)
    db.scalar.return_value = now
    successes = services.EQUIPMENT_RETURNS._value.get()
    failures = services.EQUIPMENT_RETURNS_FAILS._value.get()

    assert services.return_equipment(db, 1, schemas.ReturnInput()) is result

    assert services.EQUIPMENT_RETURNS._value.get() == successes + (not already_returned)
    assert services.EQUIPMENT_RETURNS_FAILS._value.get() == failures
