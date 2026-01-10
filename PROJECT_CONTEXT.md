# AI Test Platform (Mentis) — Project Context

> **Цель документа**: Контекст для AI-ассистентов о состоянии проекта, архитектурных решениях и известных особенностях.

## 🌐 Доступ

- **Production**: https://mentis.forzone.uk
- **API Docs**: https://mentis.forzone.uk/api/docs
- **Health Check**: https://mentis.forzone.uk/api/health

---

## 📋 О проекте

**Mentis** — веб-платформа для автоматической генерации персонализированных тестов с использованием GPT-4.1 и RAG (OpenAI Vector Stores).

**Основной flow**:

1. Преподаватель загружает учебные материалы (PDF, DOCX, TXT)
2. Система векторизует документы в OpenAI Vector Store
3. AI извлекает контент через File Search и генерирует N уникальных вариантов теста
4. Студенты проходят тесты (каждому — случайный вариант)
5. Система автоматически проверяет ответы, AI оценивает эссе

---

## 🛠 Технологический стек

### Frontend

- **Vue 3** (Composition API, `<script setup>`) + **TypeScript**
- **Vite 7.1** — сборка
- **Element Plus** — UI компоненты
- **Pinia** — state management
- **Vue Router 4** — маршрутизация с guards
- **Vue I18n** — 4 языка (EN, PL, UA, RU)
- **Axios** — HTTP клиент с interceptors

### Backend

- **FastAPI 0.115** (Python 3.11) — async REST API
- **SQLAlchemy 2.0** — async ORM
- **Pydantic v2** — валидация
- **PostgreSQL 16** — БД
- **Redis 7** — кэш + Celery broker
- **Celery** — фоновые задачи (векторизация, генерация)
- **JWT** — аутентификация

### AI/RAG

- **OpenAI GPT-4.1** — генерация вопросов, оценка эссе
- **OpenAI Vector Stores** — хранение и поиск по документам
- **text-embedding-3-small** — embeddings

### Infrastructure

- **Docker Compose** — 10 сервисов
- **Nginx** — reverse proxy + frontend
- **Cloudflare Tunnel** — HTTPS без открытия портов
- **Prometheus + Grafana** — мониторинг

---

## 🏗 Архитектура и ключевые решения

### 1. Двухшаговый RAG (КРИТИЧЕСКИ ВАЖНО)

**Проблема**: OpenAI Assistant с `file_search` не использовал файлы — генерировал из своих знаний.

**Решение** (`backend/app/services/openai_vectorstore.py`):

**Шаг 1** — Извлечение контента:

```python
# Создаём assistant ТОЛЬКО для извлечения текста через file_search
assistant = client.beta.assistants.create(
    instructions="Use file_search to extract ALL text from documents",
    tools=[{"type": "file_search"}],
    tool_resources={"file_search": {"vector_store_ids": [vs_id]}}
)
# Результат: полный текст документа
```

**Шаг 2** — Генерация вопросов:

```python
# Стандартный chat completion с извлечённым текстом
response = client.chat.completions.create(
    model="gpt-4-turbo-preview",
    messages=[{"role": "user", "content": f"Generate questions from: {extracted_content}"}]
)
```

### 2. N уникальных вариантов теста

**Цель**: Предотвратить списывание — каждый студент получает уникальный вариант.

**Реализация**:

- `Question.variant_number` — номер варианта (1, 2, 3...)
- `Test.variant_number` — какой вариант назначен студенту
- При старте теста: `variant = random.choice(available_variants)`
- Вопросы фильтруются по `variant_number`

**Лимит**: максимум 10 вариантов (чтобы не перегружать OpenAI API).

### 3. Timer Mode

Два режима таймера (поле `Project.timer_mode`):

- `total` — общий лимит на весь тест (минуты)
- `per_question` — лимит на каждый вопрос (секунды)

### 4. Shuffle Options

AI склонен ставить правильный ответ первым. Решение:

- Инструкция в промпте: "RANDOMIZE the position of correct answer"
- Функция `_shuffle_options()` перемешивает варианты после генерации

---

## 🗄 Схема базы данных

```sql
users (id, email, password_hash, role, first_name, last_name, created_at)

projects (
  id, teacher_id, title, description, status,
  total_time, time_per_question, timer_mode,
  max_students, start_time, end_time,
  vector_store_id, allowed_students[], created_at
)

question_type_configs (id, project_id, type, count)

materials (id, project_id, folder_id, file_name, file_type, file_path, openai_file_id, status)

material_folders (id, teacher_id, name, description)

participants (id, teacher_id, email, first_name, last_name, type, group_id, confirmation_status, student_user_id)

participant_groups (id, teacher_id, name, description)

questions (
  id, project_id, variant_number, type, text, points,
  options[], correct_answer, correct_answers[],
  matching_pairs, explanation, order
)

tests (id, project_id, student_id, variant_number, status, score, max_score, started_at, completed_at)

answers (id, test_id, question_id, answer, is_correct, score, feedback, ai_grading_details, graded_by)

student_emails (id, user_id, email, is_primary, institution)
```

**Миграции** (8 штук в `backend/alembic/versions/`):

1. `001_initial.py` — базовые таблицы
2. `002_openai_vectorstore.py` — vector_store_id
3. `003_participant_confirmation.py` — confirmation_status
4. `004_test_variants.py` — variant_number
5. `005_project_num_variants.py` — num_variants в projects
6. `006_test_language.py` — language поле
7. `007_ai_grading.py` — ai_grading_details, graded_by
8. `008_timer_mode.py` — timer_mode

---

## 🔌 API Endpoints (основные)

### Auth (`/api/v1/auth`)

| Method | Path        | Описание             |
| ------ | ----------- | -------------------- |
| POST   | `/register` | Регистрация          |
| POST   | `/login`    | Вход (JWT)           |
| GET    | `/me`       | Текущий пользователь |

### Projects (`/api/v1/projects`)

| Method         | Path                    | Описание                            |
| -------------- | ----------------------- | ----------------------------------- |
| GET/POST       | `/`                     | CRUD проектов                       |
| GET/PUT/DELETE | `/{id}`                 | Операции с проектом                 |
| POST           | `/{id}/materials`       | Привязать материалы                 |
| POST           | `/{id}/settings`        | Настроить параметры                 |
| POST           | `/{id}/vectorize`       | Запустить векторизацию              |
| POST           | `/{id}/generate-tests`  | Генерация тестов (Celery)           |
| GET            | `/{id}/questions`       | Список вопросов (фильтр по variant) |
| CRUD           | `/{id}/questions/{qid}` | Операции с вопросами                |
| CRUD           | `/{id}/students`        | Управление студентами проекта       |
| PATCH          | `/{id}/schedule`        | Запланировать тест                  |
| POST           | `/{id}/complete`        | Завершить проект (status→completed) |
| GET            | `/{id}/test-results`    | Результаты всех тестов проекта      |

### Materials (`/api/v1/materials`)

| Method | Path       | Описание           |
| ------ | ---------- | ------------------ |
| GET    | `/`        | Список материалов  |
| POST   | `/upload`  | Загрузка файла     |
| CRUD   | `/folders` | Управление папками |

### Participants (`/api/v1/participants`)

| Method   | Path            | Описание                |
| -------- | --------------- | ----------------------- |
| GET/POST | `/`             | CRUD участников         |
| GET      | `/lookup`       | Поиск студента по email |
| POST     | `/{id}/confirm` | Подтвердить приглашение |
| CRUD     | `/groups`       | Управление группами     |

### Student (`/api/v1/student`)

| Method | Path                        | Описание           |
| ------ | --------------------------- | ------------------ |
| GET    | `/dashboard`                | Dashboard студента |
| GET    | `/tests/available`          | Доступные тесты    |
| POST   | `/tests/{project_id}/start` | Начать тест        |
| POST   | `/tests/{test_id}/submit`   | Отправить ответы   |
| GET    | `/tests/{test_id}/results`  | Результаты         |

---

## 🐛 Решённые технические проблемы

### 1. Falsy Value Bug (correctAnswer = 0)

**Проблема**: `correctAnswer: 0` сохранялось как `null`.

```python
# НЕПРАВИЛЬНО: 0 or x → x
correct_answer = q_data.get("correctAnswer") or q_data.get("correctAnswers")
# ПРАВИЛЬНО:
correct_answer = q_data.get("correctAnswer")
if correct_answer is None:
    correct_answer = q_data.get("correctAnswers")
```

### 2. DateTime Timezone

Backend хранит naive datetime. Frontend отправляет с timezone — backend strip'ает:

```python
start_time = data.start_time.replace(tzinfo=None) if data.start_time.tzinfo else data.start_time
```

### 3. SQLAlchemy Multiple Foreign Keys

`Participant` имеет два FK к `User`. Решение — явно указать FK:

```python
participants = relationship("Participant", foreign_keys="[Participant.teacher_id]")
```

### 4. OpenAI File ID Stale

Файлы удалены из OpenAI панели, но `openai_file_id` в БД. Очистка:

```bash
docker exec mentis_backend python -c "
from app.db.session import sync_session_maker
from app.models.material import Material
from sqlalchemy import update
with sync_session_maker() as db:
    db.execute(update(Material).values(openai_file_id=None))
    db.commit()
"
```

### 5. i18n @ Symbol

Vue-i18n интерпретирует `@` как linked message. Экранировать: `student{'@'}university.edu`

---

## 📊 Текущий статус компонентов

| Компонент            | Статус      | Примечание                      |
| -------------------- | ----------- | ------------------------------- |
| Frontend (Vue 3)     | ✅ Готов    | Все views реализованы           |
| Backend (FastAPI)    | ✅ Готов    | Все endpoints                   |
| PostgreSQL           | ✅ Работает | 8 миграций                      |
| Redis + Celery       | ✅ Работает | Векторизация, генерация         |
| OpenAI Vector Stores | ✅ Работает | Двухшаговый RAG                 |
| Nginx + Cloudflare   | ✅ Работает | HTTPS                           |
| AI Generation        | ✅ Работает | Контент из документов           |
| Test Variants        | ✅ Работает | N вариантов                     |
| Score Calculation    | ✅ Работает | По варианту                     |
| Timer Mode           | ✅ Работает | total/per_question              |
| Options Shuffle      | ✅ Работает | Рандомизация                    |
| AI Grading           | 🔶 Готово   | Требует тестирования            |
| WebSocket Lobby      | ❌ Удалён   | Заменён на REST polling         |
| Statistics View      | ❌ Удалён   | Статистика показана в LobbyView |

---

## 🔄 Последние изменения (Январь 2026)

### Удалённые компоненты

1. **WebSocket в LobbyView** — полностью удалён. Теперь используется REST API polling (каждые 10 сек для обновления результатов). Файл `websocket.service.ts` существует, но не используется в Lobby.

2. **ProjectStatisticsView.vue** — удален, маршрут закомментирован. Статистика теперь отображается прямо в LobbyView (таблица результатов тестов).

### Изменения в LobbyView

- Убрана иконка "Live" (WebSocket статус)
- Кнопка "Запланировать тест" активна для `completed` проектов
- Кнопка "Начать тест" → "Перезапустить тест" для `completed` (оранжевая, кликабельна)
- При перезапуске тест снова активен на 60 минут

### Изменения в TeacherDashboardView

- Кнопка "Lobby" показывается для статусов: `ready`, `active`, `completed`
- Кнопка "Statistics" удалена (статистика в Lobby)

### Исправленные баги

1. **Timezone/Countdown** — Добавлена функция `formatUtcToLocal()` для корректного отображения обратного отсчёта. Backend хранит UTC без 'Z', JS интерпретировал как local time.

2. **Availability Window** — Изменено с `totalTime` (длительность теста) на фиксированные 60 минут для окна доступности при ручной активации.

3. **Complete endpoint 500** — `POST /projects/{id}/complete` падал с `NameError: ProjectSettings`. Исправлено на `ProjectSettingsBase`.

4. **AppenderQuery len()** — В `/complete` endpoint добавлен `selectinload(Project.questions)` для корректного подсчёта вопросов.

### Новые локализации

- `teacher.testInProgress` — "Тест в процессе"
- `teacher.testCompleted` — "Тест завершён"
- `teacher.restartTest` — "Перезапустить Тест"

---

## ⚠️ Известные особенности

1. **OpenAI file_id**: Если файлы удалены из OpenAI панели — очистить `openai_file_id` в БД.
2. **Лимит вариантов**: Максимум 10.
3. **Timezone**: Backend хранит naive datetime (UTC без 'Z'). Frontend должен добавлять 'Z' при парсинге для корректного отображения.
4. **JWT**: Access 30 мин, refresh 7 дней. `localStorage.token`.
5. **Тема/Язык**: `localStorage.theme`, `localStorage.locale`.
6. **Availability Window**: При ручной активации теста — 60 минут (не totalTime).
7. **Статус проекта**: `draft` → `ready` → `active` → `completed`. Можно перезапустить из `completed` в `active`.

---

## 🔧 Команды для работы

```bash
# Сборка и запуск
docker-compose up -d --build

# Пересборка конкретных сервисов
docker-compose up -d --build backend celery_worker nginx

# Применить миграции
docker exec mentis_backend alembic upgrade head

# Логи
docker logs mentis_backend --tail 50
docker logs mentis_celery_worker --tail 100

# Статус
docker ps
```

---

## 🚧 TODO / В работе

### Приоритет 1 (Критично)

- [x] ~~WebSocket для Lobby~~ — **Удалён**, заменён на REST polling
- [ ] Тестирование AI Grading для эссе
- [x] Review interface — учитель просматривает ответы (TestReviewView.vue)

### Приоритет 2 (Важно)

- [ ] Manual override — ручная корректировка AI-оценки
- [ ] Статистика по вариантам
- [ ] Export результатов в Excel/PDF

### Приоритет 3 (Улучшения)

- [ ] Email уведомления
- [ ] Расширенная аналитика
- [ ] Mobile-friendly UI

---

## 📁 Ключевые файлы

### Frontend

- `src/types/index.ts` — TypeScript интерфейсы
- `src/services/` — API сервисы
- `src/stores/` — Pinia stores
- `src/router/index.ts` — маршруты
- `src/views/LobbyView.vue` — главная страница управления тестом (статистика, результаты, запуск)
- `src/views/TeacherDashboardView.vue` — список проектов учителя
- `src/i18n/locales/` — локализации (en.ts, ru.ts, ua.ts, pl.ts)

### Backend

- `backend/app/core/config.py` — настройки
- `backend/app/api/v1/endpoints/projects.py` — API проектов (включая /complete endpoint)
- `backend/app/models/` — SQLAlchemy модели
- `backend/app/services/openai_vectorstore.py` — RAG логика
- `backend/app/tasks/` — Celery задачи

### Удалённые/Неактивные файлы

- `src/views/ProjectStatisticsView.vue.bak` — старая страница статистики
- `src/services/websocket.service.ts` — существует, но не используется в Lobby

---

## 💡 Советы для следующей модели

1. **Пересборка проекта**: `docker-compose up -d --build` или для конкретных сервисов `docker-compose up -d --build backend nginx`

2. **Логи ошибок**: `docker logs mentis_backend --tail 50` — бэкенд логирует все ошибки с traceback

3. **Поиск по коду**: Используй `grep_search` для поиска использования функций/компонентов

4. **Локализация**: При добавлении новых строк UI — обновляй все 4 файла локализации (en, ru, ua, pl)

5. **Pydantic v2**: Используй `model_dump()` вместо `.dict()`, `model_validate()` вместо `parse_obj()`

6. **SQLAlchemy relationships**: Для доступа к lazy-loaded relationships используй `selectinload()` в запросах

7. **Status flow проекта**:
   - `draft` — проект создан, материалы не загружены
   - `ready` — тесты сгенерированы, можно активировать
   - `active` — тест идёт, студенты могут проходить
   - `completed` — тест завершён, можно перезапустить

---

_Последнее обновление: 10 января 2026_
