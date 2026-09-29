from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app import schemas as s
from app import services
from app.db import get_session

DB = Annotated[Session, Depends(get_session)]
RecordId = Annotated[int, Path(gt=0, le=9223372036854775807)]


class ListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    q: str = Field(default="", max_length=200)
    sort: str | None = None
    desc: bool = False
    category_id: s.Id | None = None
    model_id: s.Id | None = None
    employee_id: s.Id | None = None
    equipment_id: s.Id | None = None
    operational_state: s.State | None = None
    is_active: bool | None = None
    available: bool | None = None
    open: bool | None = None


router = APIRouter(
    prefix="/api/v1",
    responses={status: {"model": s.ErrorResponse} for status in (404, 409, 422, 503, 500)},
)


def register_crud(resource, create_schema, patch_schema, output_schema):
    """Four identical HTTP contracts; domain behavior stays in explicit service functions."""
    child = APIRouter(prefix=f"/{resource}", tags=[resource])

    @child.get("", response_model=s.Page[output_schema], name=f"list_{resource}")
    def listing(db: DB, query: Annotated[ListQuery, Query()]):
        return services.list_records(db, resource, query)

    @child.get("/{id}", response_model=output_schema, name=f"read_{resource}")
    def read(id: RecordId, db: DB):
        return services.read_record(db, resource, id)

    @child.post("", response_model=output_schema, status_code=201, name=f"create_{resource}")
    def create(body: create_schema, db: DB):
        return services.create_record(db, resource, body)

    @child.patch("/{id}", response_model=output_schema, name=f"update_{resource}")
    def update(id: RecordId, body: patch_schema, db: DB):
        return services.update_record(db, resource, id, body)

    @child.delete("/{id}", status_code=204, name=f"delete_{resource}")
    def delete(id: RecordId, db: DB):
        services.delete_record(db, resource, id)
        return Response(status_code=204)

    router.include_router(child)


register_crud("categories", s.CategoryCreate, s.CategoryPatch, s.CategoryOut)
register_crud("equipment-models", s.ModelCreate, s.ModelPatch, s.ModelOut)
register_crud("employees", s.EmployeeCreate, s.EmployeePatch, s.EmployeeOut)
register_crud("equipment", s.EquipmentCreate, s.EquipmentPatch, s.EquipmentOut)


@router.get("/assignments", response_model=s.Page[s.AssignmentOut], tags=["assignments"])
def list_assignments(db: DB, query: Annotated[ListQuery, Query()]):
    return services.list_records(db, "assignments", query)


@router.get("/assignments/{id}", response_model=s.AssignmentOut, tags=["assignments"])
def read_assignment(id: RecordId, db: DB):
    return services.read_record(db, "assignments", id)


@router.post("/assignments", response_model=s.AssignmentOut, status_code=201, tags=["assignments"])
def issue(body: s.AssignmentCreate, db: DB):
    return services.issue(db, body)


@router.put("/assignments/{id}/return", response_model=s.AssignmentOut, tags=["assignments"])
def return_equipment(id: RecordId, body: s.ReturnInput, db: DB):
    return services.return_equipment(db, id, body)
