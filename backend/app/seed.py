"""Repeatable synthetic fixtures. Existing records are verified, never overwritten."""

from datetime import UTC, datetime

from sqlalchemy import func, select, text

from app import models as m
from app.db import SessionLocal


class SeedConflict(Exception):
    pass


def ensure(db, entity, predicate, values):
    row = db.scalar(select(entity).where(predicate).with_for_update())
    if row is None:
        row = entity(**values)
        db.add(row)
        db.flush()
    elif any(getattr(row, key) != value for key, value in values.items()):
        raise SeedConflict(f"Изменена демонстрационная запись {entity.__tablename__} id={row.id}")
    return row


def seed(db):
    with db.begin():
        # Serialize simultaneous seed runs; all inserts/verification share one transaction.
        db.execute(text("SELECT pg_advisory_xact_lock(9241803)"))
        categories = []
        for name in ("Ноутбуки", "Мониторы", "Периферия"):
            categories.append(
                ensure(
                    db,
                    m.Category,
                    func.lower(func.trim(m.Category.name)) == name.lower(),
                    {
                        "name": name,
                        "description": "Демонстрационная категория",
                    },
                )
            )
        models = []
        for category, manufacturer, name in (
            (categories[0], "Lenovo", "ThinkPad T14"),
            (categories[0], "Apple", "MacBook Air 13"),
            (categories[1], "Dell", "UltraSharp U2724D"),
            (categories[2], "Logitech", "MX Keys"),
        ):
            models.append(
                ensure(
                    db,
                    m.EquipmentModel,
                    (func.lower(func.trim(m.EquipmentModel.manufacturer)) == manufacturer.lower())
                    & (func.lower(func.trim(m.EquipmentModel.name)) == name.lower()),
                    {
                        "category_id": category.id,
                        "manufacturer": manufacturer,
                        "name": name,
                        "description": "Учебная модель",
                    },
                )
            )
        employees = []
        for index, name in enumerate(
            ("Анна Демонстрационная", "Иван Примеров", "Мария Учебная"), 1
        ):
            number = f"DEMO-{index:03}"
            employees.append(
                ensure(
                    db,
                    m.Employee,
                    m.Employee.personnel_number == number,
                    {
                        "personnel_number": number,
                        "full_name": name,
                        "email": None,
                        "is_active": index != 3,
                    },
                )
            )
        equipment = []
        for index, (model_index, state) in enumerate(
            (
                (0, "usable"),
                (1, "usable"),
                (2, "usable"),
                (3, "usable"),
                (0, "unavailable"),
                (2, "retired"),
                (0, "usable"),
                (2, "usable"),
            ),
            1,
        ):
            number = f"DEMO-EQ-{index:03}"
            equipment.append(
                ensure(
                    db,
                    m.Equipment,
                    m.Equipment.inventory_number == number,
                    {
                        "inventory_number": number,
                        "model_id": models[model_index].id,
                        "serial_number": f"SYNTHETIC-{index:04}",
                        "operational_state": state,
                        "notes": "Синтетические данные для обучения SRE",
                    },
                )
            )
        for eq_index, employee_index, day, returned_day in (
            (0, 2, 10, 20),
            (0, 0, 22, None),
            (2, 1, 25, None),
        ):
            issued = datetime(2026, 9, day, 9, tzinfo=UTC)
            values = {
                "equipment_id": equipment[eq_index].id,
                "employee_id": employees[employee_index].id,
                "issued_at": issued,
                "returned_at": datetime(2026, 9, returned_day, 10, tzinfo=UTC)
                if returned_day
                else None,
                "issue_note": "Демонстрационная выдача",
                "return_note": "Возвращено в комплекте" if returned_day else None,
            }
            ensure(
                db,
                m.Assignment,
                (m.Assignment.equipment_id == values["equipment_id"])
                & (m.Assignment.issued_at == issued),
                values,
            )


if __name__ == "__main__":
    try:
        with SessionLocal() as session:
            seed(session)
    except SeedConflict as exc:
        raise SystemExit(f"Seed отменён целиком: {exc}") from None
    print("Демонстрационные данные созданы или проверены; существующие записи сохранены.")
