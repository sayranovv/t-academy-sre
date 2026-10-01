import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import SessionLocal, engine
from app.main import app


@pytest.fixture
def clean_db():
    # Never truncate the developer's persistent database, even if invoked incorrectly.
    assert engine.url.database == "equipment_test", "Use make test (isolated PostgreSQL)"
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE assignments, equipment, equipment_models, employees, categories "
                "RESTART IDENTITY"
            )
        )
    yield


@pytest.fixture
def client(clean_db):
    with TestClient(app) as client:
        yield client


@pytest.fixture
def records(client):
    def create(resource, body):
        response = client.post(f"/api/v1/{resource}", json=body)
        assert response.status_code == 201, response.text
        return response.json()

    category = create("categories", {"name": "Ноутбуки"})
    model = create(
        "equipment-models", {"category_id": category["id"], "manufacturer": "Lenovo", "name": "T14"}
    )
    equipment = create("equipment", {"model_id": model["id"], "inventory_number": " eq-01 "})
    employee = create(
        "employees", {"personnel_number": " e-01 ", "full_name": "Тестовый сотрудник"}
    )
    return {"category": category, "model": model, "equipment": equipment, "employee": employee}


@pytest.fixture
def session(clean_db):
    with SessionLocal() as session:
        yield session
