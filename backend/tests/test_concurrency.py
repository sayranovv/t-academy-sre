"""Deterministic interleavings: first writer holds a row, second is observed waiting in PG."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic

import pytest
from sqlalchemy import event, text

from app import schemas as s
from app import services
from app.db import SessionLocal, engine


def interleave(first, second, lock_table=None):
    locked, release, second_connected = Event(), Event(), Event()
    second_pid = []

    def first_worker():
        with SessionLocal() as db:

            def pause(conn, cursor, statement, parameters, context, executemany):
                matches = lock_table is None or f"FROM {lock_table} " in statement
                if "FOR UPDATE" in statement and matches and not locked.is_set():
                    locked.set()
                    assert release.wait(5)

            event.listen(
                db,
                "after_begin",
                lambda session, transaction, conn: event.listen(
                    conn, "after_cursor_execute", pause
                ),
            )
            try:
                return first(db)
            except services.DomainError as exc:
                return exc.code

    def second_worker():
        with SessionLocal() as db:

            def identify(session, transaction, conn):
                second_pid.append(conn.scalar(text("SELECT pg_backend_pid()")))
                second_connected.set()

            event.listen(db, "after_begin", identify)
            try:
                return second(db)
            except services.DomainError as exc:
                return exc.code

    with ThreadPoolExecutor(2) as executor:
        a = executor.submit(first_worker)
        try:
            assert locked.wait(5)
            b = executor.submit(second_worker)
            assert second_connected.wait(5)
            deadline = monotonic() + 1.5
            with engine.connect() as observer:
                while monotonic() < deadline:
                    if observer.scalar(
                        text(
                            "SELECT wait_event_type = 'Lock' FROM pg_stat_activity WHERE pid = :pid"
                        ),
                        {"pid": second_pid[0]},
                    ):
                        break
                    observer.rollback()  # release statistics snapshot before next observation
                else:
                    raise AssertionError("Second writer did not wait for the row lock")
        finally:
            release.set()
        return a.result(timeout=5), b.result(timeout=5)


def issue(db):
    return services.issue(db, s.AssignmentCreate(equipment_id=1, employee_id=1))


@pytest.mark.parametrize(
    "operation,expected",
    [
        (lambda db: issue(db), "equipment_already_assigned"),
        (
            lambda db: services.update_record(db, "employees", 1, s.EmployeePatch(is_active=False)),
            "employee_has_equipment",
        ),
    ],
)
def test_issue_wins_employee_races(records, operation, expected):
    first, second = interleave(issue, operation)
    assert first.id > 0
    assert second == expected


@pytest.mark.parametrize(
    "resource,body,expected",
    [
        ("employees", s.EmployeePatch(is_active=False), "employee_inactive"),
        ("equipment", s.EquipmentPatch(operational_state="retired"), "equipment_unavailable"),
    ],
)
def test_state_change_wins_issue_race(records, resource, body, expected):
    _, second = interleave(lambda db: services.update_record(db, resource, 1, body), issue)
    assert second == expected


def test_double_issue_by_different_employees(records, client):
    client.post("/api/v1/employees", json={"personnel_number": "SECOND", "full_name": "Другой"})
    first, second = interleave(
        issue,
        lambda db: services.issue(db, s.AssignmentCreate(equipment_id=1, employee_id=2)),
        lock_table="equipment",
    )
    assert first.id > 0
    assert second == "equipment_already_assigned"


def test_issue_wins_retirement_race(records):
    _, second = interleave(
        issue,
        lambda db: services.update_record(
            db, "equipment", 1, s.EquipmentPatch(operational_state="retired")
        ),
        lock_table="equipment",
    )
    assert second == "equipment_already_assigned"
