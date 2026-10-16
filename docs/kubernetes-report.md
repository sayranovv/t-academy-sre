# Запуск приложения учёта оборудования в minikube

Приложение состоит из API на FastAPI, интерфейса на Vue и базы PostgreSQL. Для запуска в Kubernetes я использовал однодовый кластер minikube с профилем `sre`, драйвером Docker и runtime Docker. Ресурсы приложения находятся в namespace `default`. Манифесты лежат в каталоге `k8s/`.

API и frontend работают из локально собранных образов `t-academy-equipment-api:0.1.0` и `t-academy-equipment-web:0.1.0`. Образ frontend содержит собранный интерфейс и Nginx. Для базы используется готовый образ `postgres:18.3-bookworm`.

## Какие абстракции Kubernetes использованы

| Абстракция | Ресурсы проекта | Для чего используется |
|---|---|---|
| Deployment | `api-deployment`, `web-deployment`, `db-deployment` | Описывает запуск компонентов и поддерживает заданное количество Pod |
| Pod | Pod API, frontend и PostgreSQL | Запускает контейнер компонента. В каждом Pod приложения находится один контейнер |
| Service, тип ClusterIP | `api`, `web`, `db` | Даёт компоненту постоянный сетевой адрес внутри кластера и выбирает его Pod по меткам |
| Secret | `db-secret` | Хранит пароль базы. API, PostgreSQL и Job миграций получают его из ключа `password` |
| ConfigMap | `web-config` | Хранит конфигурацию Nginx для работы в Kubernetes |
| PersistentVolumeClaim | `db-pvc` | Запрашивает 1 GiB хранилища для PostgreSQL с режимом доступа `ReadWriteOnce` |
| Job | `db-migrate` | Выполняет `alembic upgrade head` для создания и обновления схемы базы |

Deployment создаёт ReplicaSet, который поддерживает нужное число Pod. Отдельные манифесты Pod и ReplicaSet для приложения я не писал. В исходных манифестах у API две реплики, у frontend и PostgreSQL по одной. Для демонстрации масштабирования предусмотрено увеличение API до трёх реплик, а frontend до двух.

PostgreSQL использует стратегию обновления `Recreate`: при обновлении Deployment старый Pod удаляется до создания нового. База остаётся в одной реплике. Простое увеличение числа Pod PostgreSQL не настроит репликацию данных.

PVC связан с PersistentVolume, который выделяет provisioner minikube через StorageClass по умолчанию. Контейнер PostgreSQL подключает это хранилище к `/var/lib/postgresql`. Данные сохраняются при замене Pod базы, пока сохраняется само хранилище. Это локальное хранилище учебного кластера, а не резервная копия.

Job миграций использует образ API и те же настройки подключения к PostgreSQL. Он запускается после готовности базы и завершается после выполнения команды. API и frontend запускаются после успешных миграций.

## Как взаимодействуют сервисы

```text
Браузер: http://localhost:8080
    |
    | kubectl port-forward svc/web 8080:8080
    v
Pod frontend с Nginx:8080, выбранный Service web
    |
    | HTTP/1.1, запросы /api/v1/...
    v
Service api:8000 -> Pod API:8000
    |
    | протокол PostgreSQL
    v
Service db:5432 -> Pod PostgreSQL:5432 -> хранилище db-pvc
```

Для доступа с компьютера я использую `kubectl port-forward`. Команда выбирает Pod через Service `web` и перенаправляет на него локальный порт 8080. Браузер получает от Nginx файлы интерфейса, а Vue отправляет REST-запросы на относительный адрес `/api/v1` того же сайта.

Nginx перенаправляет запросы API на `http://api.default.svc.cluster.local:8000`. Полное DNS-имя указывает на Service `api` в namespace `default`. В ConfigMap указан resolver `10.96.0.10`, адрес DNS-сервиса текущего кластера. Для другого кластера этот адрес нужно проверить заново.

Service `api` выбирает Pod с меткой `app: api`. API подключается к PostgreSQL по адресу `db:5432`. Имя `db` разрешается через DNS Kubernetes в адрес Service базы, который выбирает Pod с меткой `app: db`. PostgreSQL принимает соединения от API и Job миграций, браузер с базой напрямую не взаимодействует.

API получает параметры подключения через переменные `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` и `DB_PASSWORD`. Контейнер PostgreSQL использует `POSTGRES_DB`, `POSTGRES_USER` и `POSTGRES_PASSWORD`. В обоих случаях пароль берётся из одного Secret.

Конфигурация из `web-config` подключается как файл `/etc/nginx/nginx.conf` через `subPath`. Она задаёт порт 8080, адрес API и правила обработки маршрутов Vue. При изменении этой ConfigMap нужно пересоздать Pod frontend, чтобы контейнер получил новый файл.

API хранит данные в PostgreSQL, поэтому его реплики используют общую базу. Frontend раздаёт одни и те же файлы интерфейса и обращается к тому же Service API. При увеличении числа реплик адреса `api` и `web` остаются прежними. Масштабирование в этом учебном кластере увеличивает число Pod на одном узле, но не защищает от отказа самого узла.

## Подготовка Secret

В репозитории хранится шаблон `k8s/db-secret.yml.example`. Перед первым запуском нужно скопировать его в `k8s/db-secret.yml` и заменить `REPLACE_WITH_LOCAL_PASSWORD` своим паролем. Локальный файл с паролем исключён через `.gitignore`.

```bash
cp k8s/db-secret.yml.example k8s/db-secret.yml
# Указать пароль в локальном файле перед применением.
kubectl -n default apply -f k8s/db-secret.yml
```
