from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import IntegrityError, OperationalError

from app import services


@pytest.mark.parametrize("resource", ["equipment", "employees", "categories"])
@pytest.mark.parametrize("stage", ["flush", "commit"])
def test_create_counts_only_equipment_technical_failures(monkeypatch, resource, stage):
    db = MagicMock()
    body = MagicMock()
    body.model_dump.return_value = {}
    monkeypatch.setattr(services, "read_record", lambda *args: object())
    failure = OperationalError("", {}, RuntimeError("database unavailable"))
    if stage == "flush":
        db.flush.side_effect = failure
    else:
        db.begin.return_value.__exit__.side_effect = failure
    successes = services.EQUIPMENT_CREATED._value.get()
    failures = services.EQUIPMENT_CREATED_FAILS._value.get()
    employees = services.EMPLOYEES_CREATED._value.get()

    with pytest.raises(OperationalError) as caught:
        services.create_record(db, resource, body)

    assert caught.value is failure
    assert services.EQUIPMENT_CREATED._value.get() == successes
    assert services.EMPLOYEES_CREATED._value.get() == employees
    assert services.EQUIPMENT_CREATED_FAILS._value.get() == failures + (resource == "equipment")


@pytest.mark.parametrize(
    "failure",
    [
        services.DomainError("not_found", "Запись не найдена", 404),
        IntegrityError("", {}, RuntimeError("constraint conflict")),
    ],
)
def test_create_excludes_expected_rejections(monkeypatch, failure):
    db = MagicMock()
    body = MagicMock()
    body.model_dump.return_value = {}
    monkeypatch.setattr(services, "validate_references", MagicMock(side_effect=failure))
    successes = services.EQUIPMENT_CREATED._value.get()
    failures = services.EQUIPMENT_CREATED_FAILS._value.get()

    with pytest.raises(type(failure)) as caught:
        services.create_record(db, "equipment", body)

    assert caught.value is failure
    assert services.EQUIPMENT_CREATED._value.get() == successes
    assert services.EQUIPMENT_CREATED_FAILS._value.get() == failures
