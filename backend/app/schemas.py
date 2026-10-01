from datetime import datetime
from typing import Annotated, ClassVar, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, EmailStr, Field, model_validator


def trim(value):
    return value.strip() if isinstance(value, str) else value


def optional_text(value):
    return trim(value) or None if isinstance(value, str) else value


Name = Annotated[str, BeforeValidator(trim), Field(min_length=1, max_length=120)]
LongName = Annotated[str, BeforeValidator(trim), Field(min_length=1, max_length=200)]
Note = Annotated[Annotated[str, Field(max_length=2000)] | None, BeforeValidator(optional_text)]
Serial = Annotated[Annotated[str, Field(max_length=120)] | None, BeforeValidator(optional_text)]
Number = Annotated[
    str,
    BeforeValidator(lambda v: v.strip().upper() if isinstance(v, str) else v),
    Field(min_length=1, max_length=64, pattern=r"^[A-Z0-9._-]+$"),
]
Id = Annotated[int, Field(gt=0, le=9223372036854775807)]
State = Literal["usable", "unavailable", "retired"]
Email = Annotated[Annotated[EmailStr, Field(max_length=254)] | None, BeforeValidator(optional_text)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Patch(Input):
    nonnull: ClassVar[set[str]] = set()

    @model_validator(mode="after")
    def reject_null_required_fields(self):
        for key in self.model_fields_set & self.nonnull:
            if getattr(self, key) is None:
                raise ValueError(f"Поле {key} не может быть null")
        return self


class CategoryCreate(Input):
    name: Name
    description: Note = None


class CategoryPatch(Patch):
    nonnull = {"name"}
    name: Name | None = None
    description: Note = None


class ModelCreate(Input):
    category_id: Id
    manufacturer: Name
    name: LongName
    description: Note = None


class ModelPatch(Patch):
    nonnull = {"category_id", "manufacturer", "name"}
    category_id: Id | None = None
    manufacturer: Name | None = None
    name: LongName | None = None
    description: Note = None


class EmployeeCreate(Input):
    personnel_number: Number
    full_name: LongName
    email: Email = None


class EmployeePatch(Patch):
    nonnull = {"personnel_number", "full_name", "is_active"}
    personnel_number: Number | None = None
    full_name: LongName | None = None
    email: Email = None
    is_active: bool | None = None


class EquipmentCreate(Input):
    inventory_number: Number
    model_id: Id
    serial_number: Serial = None
    notes: Note = None


class EquipmentPatch(Patch):
    nonnull = {"inventory_number", "model_id", "operational_state"}
    inventory_number: Number | None = None
    model_id: Id | None = None
    serial_number: Serial = None
    operational_state: State | None = None
    notes: Note = None


class AssignmentCreate(Input):
    equipment_id: Id
    employee_id: Id
    issue_note: Note = None


class ReturnInput(Input):
    return_note: Note = None


class Output(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int


class Timestamped(Output):
    created_at: datetime
    updated_at: datetime


class CategoryOut(Timestamped):
    name: str
    description: str | None


class ModelOut(Timestamped):
    category_id: int
    manufacturer: str
    name: str
    description: str | None
    category: CategoryOut


class EmployeeOut(Timestamped):
    personnel_number: str
    full_name: str
    email: str | None
    is_active: bool


class CurrentAssignment(Output):
    employee_id: int
    issued_at: datetime
    employee: EmployeeOut


class EquipmentShort(Timestamped):
    inventory_number: str
    model_id: int
    serial_number: str | None
    operational_state: State
    notes: str | None
    model: ModelOut


class EquipmentOut(EquipmentShort):
    available: bool = Field(description="Вычисляется: usable и отсутствует открытая выдача")
    current_assignment: CurrentAssignment | None = Field(
        description="Открытая выдача с данными текущего получателя либо null"
    )


class AssignmentOut(Output):
    equipment_id: int
    employee_id: int
    issued_at: datetime
    returned_at: datetime | None
    issue_note: str | None
    return_note: str | None
    employee: EmployeeOut
    equipment: EquipmentShort


class Page[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list[dict] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: ErrorDetail
    request_id: str
