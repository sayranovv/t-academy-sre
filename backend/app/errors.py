import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.exc import TimeoutError as PoolTimeout
from starlette.exceptions import HTTPException

from app.services import DomainError

logger = logging.getLogger(__name__)


def error_response(request, status, code, message, details=None):
    return JSONResponse(
        status_code=status,
        content={
            "error": {"code": code, "message": message, "details": details or []},
            "request_id": getattr(request.state, "request_id", "unknown"),
        },
    )


def install_handlers(app):
    @app.exception_handler(DomainError)
    async def domain(request: Request, exc: DomainError):
        return error_response(request, exc.status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation(request: Request, exc: RequestValidationError):
        details = [
            {"field": ".".join(map(str, item["loc"][1:])), "message": item["msg"]}
            for item in exc.errors()
        ]
        return error_response(request, 422, "validation_error", "Проверьте поля формы", details)

    @app.exception_handler(IntegrityError)
    async def integrity(request: Request, exc: IntegrityError):
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", "")
        duplicates = {
            "uq_equipment_inventory_number": (
                "duplicate_inventory_number",
                "Инвентарный номер уже занят",
            ),
            "uq_employees_personnel_number": (
                "duplicate_personnel_number",
                "Табельный номер уже занят",
            ),
            "uq_categories_name_normalized": ("duplicate_category", "Категория уже существует"),
            "uq_models_manufacturer_name": ("duplicate_model", "Модель уже существует"),
            "uq_assignments_open_equipment": (
                "equipment_already_assigned",
                "Оборудование уже выдано",
            ),
        }
        if constraint in duplicates:
            code, message = duplicates[constraint]
        elif getattr(exc.orig, "sqlstate", "") == "23503":
            code, message = (
                "resource_in_use",
                "Запись связана с другими данными. Удаление невозможно",
            )
        else:
            code, message = "constraint_conflict", "Изменение нарушает ограничения данных"
        return error_response(request, 409, code, message)

    @app.exception_handler(DBAPIError)
    @app.exception_handler(PoolTimeout)
    async def database(request: Request, exc):
        # Do not log SQL parameters, connection strings or user data.
        logger.error("Database request failed (%s)", type(exc).__name__)
        return error_response(
            request, 503, "database_unavailable", "База данных временно недоступна"
        )

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return error_response(
            request, exc.status_code, "http_error", "Запрос не может быть выполнен"
        )

    @app.exception_handler(Exception)
    async def unexpected(request, exc):
        logger.error("Unhandled request error (%s)", type(exc).__name__)
        return error_response(request, 500, "internal_error", "Внутренняя ошибка сервера")
