# Учёт оборудования

Учебное приложение для курса SRE Т-Академии: каталог физических экземпляров
оборудования, сотрудники, выдача, возврат и неизменяемая история операций.

Проект включает Vue 3 SPA, REST API на FastAPI и PostgreSQL 18. Он реализован
как один репозиторий, конфигурируется через окружение и запускается в Docker Compose.
Итоговая проверка требований и 12 Factor находится в
[docs/compliance-audit.md](docs/compliance-audit.md).

## Возможности

- CRUD категорий, моделей, сотрудников и экземпляров оборудования;
- поиск, фильтры и пагинация;
- выдача только доступного оборудования активному сотруднику;
- возврат, повторная выдача и просмотр истории;
- защита от двойной выдачи на уровне транзакций и PostgreSQL;
- liveness/readiness, request ID и структурированные журналы;
- development- и production-контуры, миграции, seed и CI.

## Быстрый запуск

Нужны Docker Engine, Docker Compose v2 и `make`. Python и Node.js на хосте
для обычного запуска не требуются.

```sh
cp .env.example .env
make dev
make seed
```

Приложение: <http://localhost:5173>

OpenAPI: <http://localhost:5173/docs>

`make dev` ждёт готовности PostgreSQL, выполняет миграции отдельным процессом,
а затем запускает API и Vite. `make stop` останавливает окружение и сохраняет
volume PostgreSQL.

## Основные команды

| Команда | Назначение |
|---|---|
| `make dev` / `make stop` | Запустить или остановить development-контур |
| `make migrate` | Применить миграции отдельным процессом |
| `make seed` | Создать или проверить синтетические данные |
| `make test` | Запустить backend-тесты с PostgreSQL и Vitest |
| `make test-e2e` | Запустить пять браузерных сценариев на порту 5174 |
| `make lint` | Проверить Python, TypeScript и ESLint |
| `make build` | Собрать development- и production-образы |
| `make types` | Обновить TypeScript-типы из OpenAPI работающего API |
| `make logs` | Читать журналы development-сервисов |

Backend-тесты и e2e используют отдельную БД `equipment_test` в tmpfs и не
подключаются к рабочему volume. Не запускайте эти два набора одновременно.
Для локального Playwright дополнительно нужны Node.js 24 и установленный Chromium.

## Production-контур

```sh
cp .env.production.example .env.production
# замените POSTGRES_PASSWORD
make prod
make prod-seed
```

Интерфейс будет доступен на <http://localhost:8080>. Backend и Nginx работают
без root, frontend отдаётся как статическая сборка, API проксируется по HTTP/1.1.
Миграции выполняются до запуска API и не запускаются каждой репликой.

Две реплики API:

```sh
docker compose --env-file .env.production -f compose.production.yaml \
  up --build --wait --scale api=2
```

Остановка без удаления данных: `make prod-stop`. Для обычной остановки не используйте
`down -v`: эта команда удаляет volume PostgreSQL.

## Как устроен запрос

```text
Browser → Vite или Nginx → FastAPI → SQLAlchemy/Psycopg → PostgreSQL
```

`routes.py` описывает HTTP-контракт, `schemas.py` — входные и выходные данные,
`services.py` — транзакции и бизнес-правила, `models.py` — ORM-модель.
COMMIT завершается до успешного HTTP-ответа. Текущий получатель вычисляется по
открытой выдаче, а не хранится в карточке оборудования.

`/health/live` не обращается к БД. `/health/ready` проверяет PostgreSQL с ограниченным
временем ожидания. API и БД не публикуют порты на хосте; доступен только frontend
на localhost.

## Документация

- [Предметная область](docs/domain.md) — границы MVP, правила и критерии приёмки;
- [База данных](docs/database.md) — пять таблиц, связи, 3НФ и конкурентность;
- [Диаграммы](docs/diagrams.md) — ER, активности, состояния и компоненты;
- [Архитектура](docs/architecture.md) — REST, эксплуатационные решения и 12 Factor;
- [Дизайн-система](docs/design-system.md) — палитра, PrimeVue и состояния UI;
- [Итоговая проверка](docs/compliance-audit.md) — требования и доказательства приёмки;
- [AGENTS.md](AGENTS.md) — краткий контекст для дальнейшей работы с репозиторием.

Авторизации в учебном MVP нет. Приложение рассчитано на закрытое локальное окружение;
публичное размещение требует отдельного проектирования аутентификации.
