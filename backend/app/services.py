from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app import models as m
from app import schemas as s


class DomainError(Exception):
    def __init__(self, code: str, message: str, status: int = 409):
        self.code, self.message, self.status = code, message, status


ENTITIES = {
    "categories": (m.Category, s.CategoryOut),
    "equipment-models": (m.EquipmentModel, s.ModelOut),
    "employees": (m.Employee, s.EmployeeOut),
    "equipment": (m.Equipment, s.EquipmentOut),
    "assignments": (m.Assignment, s.AssignmentOut),
}


def require(db: Session, entity, id: int, *, lock=False):
    statement = select(entity).where(entity.id == id)
    if lock:
        statement = statement.with_for_update().execution_options(populate_existing=True)
    row = db.scalar(statement)
    if row is None:
        raise DomainError("not_found", "Запись не найдена", 404)
    return row


def loaded_query(resource):
    entity, _ = ENTITIES[resource]
    statement = select(entity).execution_options(populate_existing=True)
    if resource == "equipment-models":
        statement = statement.options(joinedload(m.EquipmentModel.category))
    elif resource == "equipment":
        statement = statement.options(
            joinedload(m.Equipment.model).joinedload(m.EquipmentModel.category),
            joinedload(m.Equipment.current_assignment).joinedload(m.Assignment.employee),
        )
    elif resource == "assignments":
        statement = statement.options(
            joinedload(m.Assignment.employee),
            joinedload(m.Assignment.equipment)
            .joinedload(m.Equipment.model)
            .joinedload(m.EquipmentModel.category),
        )
    return statement


def read_record(db, resource, id):
    entity, output = ENTITIES[resource]
    row = db.scalar(loaded_query(resource).where(entity.id == id))
    if row is None:
        raise DomainError("not_found", "Запись не найдена", 404)
    return output.model_validate(row)


def list_records(db, resource, query):
    entity, output = ENTITIES[resource]
    statement = loaded_query(resource)
    if resource == "equipment":
        statement = statement.join(m.EquipmentModel, m.Equipment.model_id == m.EquipmentModel.id)
    searchable = {
        "categories": [m.Category.name],
        "equipment-models": [m.EquipmentModel.name, m.EquipmentModel.manufacturer],
        "employees": [m.Employee.full_name, m.Employee.personnel_number],
        "equipment": [
            m.Equipment.inventory_number,
            m.Equipment.serial_number,
            m.EquipmentModel.name,
        ],
    }
    if query.q and resource in searchable:
        statement = statement.where(
            or_(*[col.icontains(query.q, autoescape=True) for col in searchable[resource]])
        )
    if resource in ("equipment", "equipment-models") and query.category_id is not None:
        statement = statement.where(m.EquipmentModel.category_id == query.category_id)
    if resource == "employees" and query.is_active is not None:
        statement = statement.where(m.Employee.is_active == query.is_active)
    if resource == "equipment":
        for key in ("model_id", "operational_state"):
            if (value := getattr(query, key)) is not None:
                statement = statement.where(getattr(m.Equipment, key) == value)
        is_assigned = (
            select(m.Assignment.id)
            .where(m.Assignment.equipment_id == m.Equipment.id, m.Assignment.returned_at.is_(None))
            .exists()
        )
        if query.available is not None:
            available = (m.Equipment.operational_state == "usable") & ~is_assigned
            statement = statement.where(available if query.available else ~available)
        if query.employee_id is not None:
            statement = statement.where(
                select(m.Assignment.id)
                .where(
                    m.Assignment.equipment_id == m.Equipment.id,
                    m.Assignment.returned_at.is_(None),
                    m.Assignment.employee_id == query.employee_id,
                )
                .exists()
            )
    if resource == "assignments":
        for key in ("equipment_id", "employee_id"):
            if (value := getattr(query, key)) is not None:
                statement = statement.where(getattr(m.Assignment, key) == value)
        if query.open is not None:
            statement = statement.where(
                m.Assignment.returned_at.is_(None)
                if query.open
                else m.Assignment.returned_at.is_not(None)
            )
    total = db.scalar(select(func.count()).select_from(statement.subquery()))
    if resource == "assignments":
        order = [m.Assignment.issued_at.desc(), m.Assignment.id.desc()]
    else:
        allowed_sort = {
            "categories": {"id", "name"},
            "equipment-models": {"id", "name", "manufacturer"},
            "employees": {"id", "full_name", "personnel_number"},
            "equipment": {"id", "inventory_number", "operational_state"},
        }
        key = query.sort or "id"
        if key not in allowed_sort[resource]:
            raise DomainError("invalid_sort", "Недопустимое поле сортировки", 422)
        column = getattr(entity, key)
        order = [column.desc() if query.desc else column.asc(), entity.id.asc()]
    rows = db.scalars(statement.order_by(*order).limit(query.limit).offset(query.offset)).all()
    return {
        "items": [output.model_validate(row) for row in rows],
        "total": total,
        "limit": query.limit,
        "offset": query.offset,
    }


def has_assignments(db, column, id, *, open_only=False):
    statement = select(m.Assignment.id).where(column == id)
    if open_only:
        statement = statement.where(m.Assignment.returned_at.is_(None))
    return db.scalar(statement.limit(1)) is not None


def validate_references(db, values):
    for key, entity in (("category_id", m.Category), ("model_id", m.EquipmentModel)):
        if key in values:
            require(db, entity, values[key])


def create_record(db, resource, body):
    entity, _ = ENTITIES[resource]
    with db.begin():
        values = body.model_dump()
        validate_references(db, values)
        row = entity(**values)
        db.add(row)
        db.flush()
        result = read_record(db, resource, row.id)
    return result


def update_record(db, resource, id, body):
    entity, _ = ENTITIES[resource]
    with db.begin():
        row = require(db, entity, id, lock=True)
        values = body.model_dump(exclude_unset=True)
        if resource == "employees" and values.get("is_active") is False:
            if has_assignments(db, m.Assignment.employee_id, id, open_only=True):
                raise DomainError(
                    "employee_has_equipment", "Сначала верните оборудование сотрудника"
                )
        if resource == "equipment":
            new_state = values.get("operational_state", row.operational_state)
            if row.operational_state == "retired" and new_state != "retired":
                raise DomainError(
                    "invalid_state_transition", "Списанное оборудование нельзя вернуть в оборот"
                )
            if new_state != "usable" and has_assignments(
                db, m.Assignment.equipment_id, id, open_only=True
            ):
                raise DomainError(
                    "equipment_already_assigned", "Сначала оформите возврат оборудования"
                )
            if values.get("model_id", row.model_id) != row.model_id and has_assignments(
                db, m.Assignment.equipment_id, id
            ):
                raise DomainError("model_is_immutable", "Модель нельзя менять после первой выдачи")
        validate_references(db, values)
        for key, value in values.items():
            setattr(row, key, value)
        db.flush()
        result = read_record(db, resource, id)
    return result


def delete_record(db, resource, id):
    entity, _ = ENTITIES[resource]
    with db.begin():
        row = require(db, entity, id, lock=True)
        db.delete(row)
        db.flush()  # PostgreSQL FK RESTRICT is the final concurrency-safe check.


def issue(db: Session, body: s.AssignmentCreate):
    with db.begin():
        employee = require(db, m.Employee, body.employee_id, lock=True)
        equipment = require(db, m.Equipment, body.equipment_id, lock=True)
        if not employee.is_active:
            raise DomainError("employee_inactive", "Сотрудник неактивен")
        if equipment.operational_state != "usable":
            raise DomainError("equipment_unavailable", "Оборудование недоступно для выдачи")
        if has_assignments(db, m.Assignment.equipment_id, equipment.id, open_only=True):
            raise DomainError("equipment_already_assigned", "Оборудование уже выдано")
        now = db.scalar(select(func.clock_timestamp()))
        previous_return = db.scalar(
            select(func.max(m.Assignment.returned_at)).where(
                m.Assignment.equipment_id == equipment.id
            )
        )
        assignment = m.Assignment(
            **body.model_dump(),
            issued_at=max(now, previous_return or now),
        )
        db.add(assignment)
        db.flush()
        result = read_record(db, "assignments", assignment.id)
    return result


def return_equipment(db: Session, id: int, body: s.ReturnInput):
    with db.begin():
        # Read only immutable FKs before locking. Refresh the assignment under lock below.
        assignment = require(db, m.Assignment, id)
        require(db, m.Employee, assignment.employee_id, lock=True)
        require(db, m.Equipment, assignment.equipment_id, lock=True)
        assignment = require(db, m.Assignment, id, lock=True)
        if assignment.returned_at is None:
            now = db.scalar(select(func.clock_timestamp()))
            assignment.returned_at = max(now, assignment.issued_at)
            assignment.return_note = body.return_note
            db.flush()
        result = read_record(db, "assignments", id)
    return result
