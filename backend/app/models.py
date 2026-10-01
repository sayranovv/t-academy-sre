from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def nonblank(column: str):
    return CheckConstraint(f"length(trim({column})) > 0", name=f"{column}_nonblank")


def note_check(column: str):
    return CheckConstraint(
        f"{column} IS NULL OR (length(trim({column})) > 0 AND length({column}) <= 2000)",
        name=f"{column}_length",
    )


def number_check(column: str):
    return CheckConstraint(f"{column} ~ '^[A-Z0-9._-]{{1,64}}$'", name=f"{column}_format")


class Timestamps:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.clock_timestamp()
    )


class Category(Timestamps, Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        nonblank("name"),
        note_check("description"),
        Index("uq_categories_name_normalized", text("lower(TRIM(BOTH FROM name))"), unique=True),
    )


class EquipmentModel(Timestamps, Base):
    __tablename__ = "equipment_models"
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )
    manufacturer: Mapped[str] = mapped_column(String(120))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[Category] = relationship(lazy="raise")
    __table_args__ = (
        nonblank("name"),
        nonblank("manufacturer"),
        note_check("description"),
        Index(
            "uq_models_manufacturer_name",
            text("lower(TRIM(BOTH FROM manufacturer))"),
            text("lower(TRIM(BOTH FROM name))"),
            unique=True,
        ),
    )


class Employee(Timestamps, Base):
    __tablename__ = "employees"
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    personnel_number: Mapped[str] = mapped_column(String(64), unique=True)
    full_name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(254))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    __table_args__ = (
        number_check("personnel_number"),
        nonblank("full_name"),
        CheckConstraint("email IS NULL OR length(trim(email)) > 0", name="email_nonblank"),
    )


class Equipment(Timestamps, Base):
    __tablename__ = "equipment"
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    inventory_number: Mapped[str] = mapped_column(String(64), unique=True)
    model_id: Mapped[int] = mapped_column(
        ForeignKey("equipment_models.id", ondelete="RESTRICT"), index=True
    )
    serial_number: Mapped[str | None] = mapped_column(String(120))
    operational_state: Mapped[str] = mapped_column(String(16), server_default="usable")
    notes: Mapped[str | None] = mapped_column(Text)
    model: Mapped[EquipmentModel] = relationship(lazy="raise")
    current_assignment: Mapped[Assignment | None] = relationship(
        primaryjoin=(
            "and_(Equipment.id == Assignment.equipment_id, Assignment.returned_at.is_(None))"
        ),
        viewonly=True,
        uselist=False,
        lazy="raise",
    )
    __table_args__ = (
        number_check("inventory_number"),
        note_check("notes"),
        CheckConstraint("operational_state IN ('usable', 'unavailable', 'retired')", name="state"),
        CheckConstraint(
            "serial_number IS NULL OR length(trim(serial_number)) > 0", name="serial_nonblank"
        ),
    )

    @property
    def available(self) -> bool:
        return self.operational_state == "usable" and self.current_assignment is None


class Assignment(Base):
    __tablename__ = "assignments"
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id", ondelete="RESTRICT"))
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="RESTRICT"))
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    issue_note: Mapped[str | None] = mapped_column(Text)
    return_note: Mapped[str | None] = mapped_column(Text)
    employee: Mapped[Employee] = relationship(lazy="raise")
    equipment: Mapped[Equipment] = relationship(lazy="raise")
    __table_args__ = (
        note_check("issue_note"),
        note_check("return_note"),
        CheckConstraint("returned_at IS NULL OR returned_at >= issued_at", name="time_order"),
        CheckConstraint(
            "returned_at IS NOT NULL OR return_note IS NULL", name="return_note_requires_return"
        ),
        Index(
            "uq_assignments_open_equipment",
            equipment_id,
            unique=True,
            postgresql_where=returned_at.is_(None),
        ),
        Index("ix_assignments_equipment_history", equipment_id, issued_at.desc(), id.desc()),
        Index("ix_assignments_employee_history", employee_id, issued_at.desc(), id.desc()),
        Index("ix_assignments_open_employee", employee_id, postgresql_where=returned_at.is_(None)),
    )
