# Диаграммы v1

Mermaid-блоки — редактируемые исходники диаграмм, отображаемые в совместимом
Markdown-просмотрщике. Полный словарь атрибутов — [database.md](database.md).
Схемы активностей ниже используют flowchart-нотацию Mermaid, не строгую UML-нотацию.

## ER: сущности и связи

```mermaid
erDiagram
    CATEGORIES ||--o{ EQUIPMENT_MODELS : groups
    EQUIPMENT_MODELS ||--o{ EQUIPMENT : describes
    EMPLOYEES ||--o{ ASSIGNMENTS : receives
    EQUIPMENT ||--o{ ASSIGNMENTS : has_history

    CATEGORIES {
        bigint id PK
        varchar name UK
        text description
        timestamptz created_at
        timestamptz updated_at
    }
    EQUIPMENT_MODELS {
        bigint id PK
        bigint category_id FK
        varchar manufacturer
        varchar name
        text description
        timestamptz created_at
        timestamptz updated_at
    }
    EMPLOYEES {
        bigint id PK
        varchar personnel_number UK
        varchar full_name
        varchar email
        boolean is_active
        timestamptz created_at
        timestamptz updated_at
    }
    EQUIPMENT {
        bigint id PK
        varchar inventory_number UK
        bigint model_id FK
        varchar serial_number
        varchar operational_state
        text notes
        timestamptz created_at
        timestamptz updated_at
    }
    ASSIGNMENTS {
        bigint id PK
        bigint equipment_id FK
        bigint employee_id FK
        timestamptz issued_at
        timestamptz returned_at
        text issue_note
        text return_note
    }
```

UK имени категории относится к нормализованному значению. Составная уникальность
производителя/имени модели и частичная уникальность открытой выдачи описаны в database.md;
обычная кардинальность ER не выражает правило «не больше одной открытой выдачи».

## Активность: выдача оборудования

```mermaid
flowchart TD
    start([Начало]) --> choose[Оператор выбирает устройство и сотрудника]
    choose --> submit[Подтвердить выдачу]
    submit --> valid{Формат запроса корректен?}
    valid -- Нет --> validation[422: показать ошибки формы]
    validation --> finish([Конец попытки])
    valid -- Да --> begin[Начать транзакцию]
    begin --> locks[Блокировать сотрудника, затем экземпляр]
    locks --> exists{Обе записи существуют?}
    exists -- Нет --> missing[Откат; 404]
    missing --> finish
    exists -- Да --> active{Сотрудник активен?}
    active -- Нет --> conflict[Откат; 409 с причиной]
    active -- Да --> usable{Устройство usable?}
    usable -- Нет --> conflict
    usable -- Да --> free{Открытой выдачи нет?}
    free -- Нет --> conflict
    free -- Да --> insert[Создать выдачу с серверным временем]
    insert --> saved{Запись успешна?}
    saved -- Конфликт уникальности --> conflict
    saved -- Другая ошибка --> failure[Откат; ошибка сервера или зависимости]
    saved -- Да --> commit[COMMIT]
    commit --> result[201: показать получателя и время]
    conflict --> refresh[Объяснить причину и обновить карточку]
    refresh --> finish
    failure --> finish
    result --> finish
```

Для краткости технические ошибки соединения/блокировки на предыдущих шагах не
прорисованы отдельными стрелками: они также прерывают транзакцию и не означают успех.

## Активность: возврат оборудования

```mermaid
flowchart TD
    start([Начало]) --> select[Оператор выбирает открытую выдачу]
    select --> confirm[Подтвердить возврат с необязательным примечанием]
    confirm --> valid{Формат корректен?}
    valid -- Нет --> invalid[422: ошибки формы]
    invalid --> finish([Конец попытки])
    valid -- Да --> begin[Начать транзакцию; найти выдачу по id]
    begin --> exists{Выдача существует?}
    exists -- Нет --> missing[Откат; 404]
    missing --> finish
    exists -- Да --> locks[Блокировать сотрудника, экземпляр, выдачу]
    locks --> closed{Уже возвращено?}
    closed -- Да --> same[Завершить транзакцию; 200 с прежним результатом]
    closed -- Нет --> update[Записать время возврата и примечание]
    update --> commit[COMMIT]
    commit --> success[200: обновить карточку и историю]
    update -- Ошибка --> error[Откат; показать ошибку]
    same --> finish
    success --> finish
    error --> finish
```

Возврат адресуется по ID выдачи, не по ID устройства: повтор старого запроса не
должен случайно закрыть следующую выдачу этого же устройства.

## Состояния экземпляра

```mermaid
stateDiagram-v2
    state "Доступно: usable, без выдачи" as Available
    state "Выдано: usable, открытая выдача" as Assigned
    state "Недоступно: unavailable" as Unavailable
    state "Списано: retired" as Retired
    [*] --> Available : Создание
    Available --> Assigned : Выдать активному сотруднику
    Assigned --> Available : Вернуть
    Available --> Unavailable : Исключить из выдачи
    Unavailable --> Available : Разрешить выдачу
    Available --> Retired : Списать
    Unavailable --> Retired : Списать
    Retired --> [*]
```

Это совокупное состояние экземпляра и его открытой выдачи. `Assigned` не отдельное
значение operational_state. Удаление карточки не бизнес-переход и показано правилами CRUD.

## Границы компонентов

```mermaid
flowchart LR
    User[Оператор] --> Browser[Браузер: Vue SPA]
    Browser -->|HTTP: статика и /api/v1| Web[Веб-сервер / reverse proxy]
    Web -->|Статические файлы| Bundle[Собранный frontend]
    Web -->|HTTP/1.1 REST JSON| Backend[Python backend]
    Backend -->|SQL / транзакции| DB[(PostgreSQL)]
    Admin[Одноразовый процесс миграций] --> DB
    Backend --> Logs[stdout / stderr]
```

Диаграмма показывает целевое окружение, а не существующее развёртывание. Несколько
backend-реплик могут использовать одну БД; балансировщик и наблюдаемость развиваются
в последующих заданиях. Браузер напрямую к PostgreSQL не подключается.
