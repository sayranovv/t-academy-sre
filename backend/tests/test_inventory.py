from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app import models as m
from app.db import SessionLocal
from app.seed import SeedConflict, seed


def test_crud_normalization_errors_and_dependencies(client, records):
    assert records["equipment"]["inventory_number"] == "EQ-01"
    assert records["employee"]["personnel_number"] == "E-01"
    assert records["equipment"]["model"]["category"]["name"] == "Ноутбуки"
    for resource, payload in (
        ("categories", {"name": "  ноутбуки "}),
        ("equipment-models", {"category_id": 1, "manufacturer": " lenovo ", "name": "t14"}),
        ("equipment", {"model_id": 1, "inventory_number": "eq-01"}),
        ("employees", {"personnel_number": "e-01", "full_name": "Другой"}),
    ):
        response = client.post(f"/api/v1/{resource}", json=payload)
        assert response.status_code == 409, response.text
        assert response.json()["request_id"] == response.headers["x-request-id"]
    for resource in ("categories", "equipment-models"):
        assert client.delete(f"/api/v1/{resource}/1").status_code == 409
    for resource in ("categories", "equipment-models", "employees", "equipment"):
        assert client.patch(f"/api/v1/{resource}/1", json={"id": 8}).status_code == 422
        assert client.get(f"/api/v1/{resource}/999").status_code == 404
    assert client.patch("/api/v1/categories/1", json={"name": None}).status_code == 422
    assert (
        client.patch("/api/v1/categories/1", json={"description": "  "}).json()["description"]
        is None
    )
    assert (
        client.post(
            "/api/v1/employees", json={"personnel_number": "Русский", "full_name": "Тест"}
        ).status_code
        == 422
    )
    assert client.patch("/api/v1/employees/1", json={"email": "wrong"}).status_code == 422
    assert (
        client.post(
            "/api/v1/equipment", json={"inventory_number": "NEW", "model_id": 999}
        ).status_code
        == 404
    )
    for resource in ("equipment", "employees", "equipment-models", "categories"):
        assert client.delete(f"/api/v1/{resource}/1").status_code == 204
        assert client.get(f"/api/v1/{resource}/1").status_code == 404


def test_assignment_lifecycle_and_immutable_history(client, records):
    first = client.post("/api/v1/assignments", json={"employee_id": 1, "equipment_id": 1})
    assert first.status_code == 201, first.text
    id = first.json()["id"]
    current = client.get("/api/v1/equipment/1").json()
    assert not current["available"]
    assert current["current_assignment"]["employee"]["id"] == 1
    for url, body in (
        ("employees/1", {"is_active": False}),
        ("equipment/1", {"operational_state": "retired"}),
        ("equipment/1", {"operational_state": "unavailable"}),
        ("equipment/1", {"model_id": 999}),
    ):
        assert client.patch(f"/api/v1/{url}", json=body).status_code == 409
    assert (
        client.post("/api/v1/assignments", json={"employee_id": 1, "equipment_id": 1}).status_code
        == 409
    )
    returned = client.put(f"/api/v1/assignments/{id}/return", json={"return_note": "OK"}).json()
    second = client.post("/api/v1/assignments", json={"employee_id": 1, "equipment_id": 1}).json()
    repeat = client.put(f"/api/v1/assignments/{id}/return", json={"return_note": "CHANGED"}).json()
    assert repeat == returned
    assert client.get("/api/v1/equipment/1").json()["current_assignment"]["id"] == second["id"]
    assert client.get("/api/v1/assignments?equipment_id=1").json()["total"] == 2
    for method in (client.patch, client.delete):
        assert method(f"/api/v1/assignments/{id}").status_code == 405
    assert client.put(f"/api/v1/assignments/{second['id']}/return", json={}).status_code == 200
    assert (
        client.patch("/api/v1/equipment/1", json={"operational_state": "retired"}).status_code
        == 200
    )
    assert (
        client.patch("/api/v1/equipment/1", json={"operational_state": "usable"}).status_code == 409
    )
    assert client.patch("/api/v1/employees/1", json={"is_active": False}).status_code == 200
    assert (
        client.post("/api/v1/assignments", json={"employee_id": 1, "equipment_id": 1}).status_code
        == 409
    )
    for resource in ("employees", "equipment"):
        assert client.delete(f"/api/v1/{resource}/1").status_code == 409


def test_search_filters_pagination_and_rollback(client, records):
    assert client.get("/api/v1/equipment?q=t14&category_id=1&available=true").json()["total"] == 1
    assert client.get("/api/v1/equipment?q=%25").json()["total"] == 0
    assert client.get("/api/v1/equipment?limit=1&offset=1").json() == {
        "items": [],
        "total": 1,
        "limit": 1,
        "offset": 1,
    }
    assert client.get("/api/v1/employees?is_active=false").json()["total"] == 0
    assert client.get("/api/v1/equipment-models?category_id=999").json()["total"] == 0
    for query in ("limit=101", "offset=-1", "sort=notes", "unknown=true"):
        assert client.get(f"/api/v1/equipment?{query}").status_code == 422
    assert (
        client.patch(
            "/api/v1/equipment/1", json={"notes": "must roll back", "model_id": 999}
        ).status_code
        == 404
    )
    assert client.get("/api/v1/equipment/1").json()["notes"] is None
    assert client.get("/api/v1/assignments?open=true").json()["total"] == 0


def test_database_constraints_without_api(client, records):
    bad_rows = [
        m.Category(name="  "),
        m.Category(name="ноутбуки"),
        m.Equipment(inventory_number="lowercase", model_id=1),
        m.Equipment(inventory_number="NEW", model_id=999),
        m.Assignment(
            equipment_id=1,
            employee_id=1,
            issued_at=datetime(2026, 1, 2, tzinfo=UTC),
            returned_at=datetime(2026, 1, 1, tzinfo=UTC),
        ),
        m.Assignment(
            equipment_id=1, employee_id=1, issued_at=datetime.now(UTC), return_note="invalid"
        ),
    ]
    for row in bad_rows:
        with SessionLocal() as db, pytest.raises(IntegrityError), db.begin():
            db.add(row)
            db.flush()
    client.post("/api/v1/assignments", json={"employee_id": 1, "equipment_id": 1})
    with SessionLocal() as db, pytest.raises(IntegrityError), db.begin():
        db.add(m.Assignment(equipment_id=1, employee_id=1, issued_at=datetime.now(UTC)))
        db.flush()


def test_seed_repeat_and_conflict_rolls_back(session):
    seed(session)
    seed(session)
    with session.begin():
        assert session.scalar(select(func.count()).select_from(m.Equipment)) == 8
        session.scalar(
            select(m.Employee).where(m.Employee.personnel_number == "DEMO-001")
        ).full_name = "Изменено пользователем"
    with pytest.raises(SeedConflict):
        seed(session)
    with session.begin():
        assert session.scalar(select(func.count()).select_from(m.Assignment)) == 3
        assert (
            session.scalar(
                select(m.Employee.full_name).where(m.Employee.personnel_number == "DEMO-001")
            )
            == "Изменено пользователем"
        )
