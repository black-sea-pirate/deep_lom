# Mentis — Technical Context for AI Assistants

> Техническая документация для AI-ассистентов и разработчиков. Содержит архитектуру, API, критические решения и известные ограничения.

## 🎯 Суть проекта

**Mentis** — веб-платформа для автоматической генерации тестов с использованием GPT-4.1 и RAG.

**Flow:**

1. Преподаватель загружает материалы (PDF, DOCX, TXT)
2. Система векторизует документы в OpenAI Vector Store
3. AI генерирует N уникальных вариантов теста через двухшаговый RAG
4. Студенты проходят тесты (каждому — случайный вариант)
5. Автоматическая проверка + AI оценка эссе

**Production:** https://mentis.forzone.uk

---

## 🛠 Технологический стек

| Layer              | Technologies                                                                         |
| ------------------ | ------------------------------------------------------------------------------------ |
| **Frontend**       | Vue 3 (Composition API), TypeScript, Vite, Element Plus, Pinia, Vue Router, Vue I18n |
| **Backend**        | FastAPI 0.115, Python 3.11, SQLAlchemy 2.0 async, Pydantic v2                        |
| **Database**       | PostgreSQL 16, Redis 7 (Celery broker)                                               |
| **AI**             | OpenAI GPT-4.1, Vector Stores (file_search)                                          |
| **Infrastructure** | Docker Compose, Nginx, Cloudflare Tunnel                                             |

---

## 🏗 Ключевые архитектурные решения

### 1. Двухшаговый RAG (КРИТИЧЕСКИ ВАЖНО)

**Проблема:** OpenAI Assistant с `file_search` не использовал загруженные файлы — генерировал из своих знаний.

**Решение** (`backend/app/services/openai_vectorstore.py`):

**Шаг 1 — Извлечение контента:**

```python
assistant = client.beta.assistants.create(
    instructions="Use file_search to extract ALL text from documents",
    tools=[{"type": "file_search"}],
    tool_resources={"file_search": {"vector_store_ids": [vs_id]}}
)
# Результат: полный текст документа
```

**Шаг 2 — Генерация вопросов:**

```python
response = client.chat.completions.create(
    model="gpt-4.1",  # Модель из settings.OPENAI_MODEL
    messages=[{"role": "user", "content": f"Generate questions from: {extracted_content}"}]
)
```

### 2. N уникальных вариантов теста

- `Question.variant_number` — номер варианта (1-10)
- `Test.variant_number` — какой вариант назначен студенту
- При старте теста: `variant = random.choice(available_variants)`
- **Лимит:** максимум 10 вариантов

### 3. Timer Mode

Поле `Project.timer_mode`:

- `total` — общий лимит на весь тест (минуты)
- `per_question` — лимит на каждый вопрос (секунды)

### 4. Shuffle Options

AI склонен ставить правильный ответ первым. Решение:

- Инструкция в промпте: "RANDOMIZE the position of correct answer"
- Функция `_shuffle_options()` перемешивает варианты после генерации

### 5. Батчевая генерация

Запросы >15 вопросов разбиваются на батчи (защита от token limit).

---

## 🗄 Схема базы данных

```sql
users (id, email, password_hash, role, first_name, last_name, is_active, is_verified)
projects (id, teacher_id, title, status, timer_mode, total_time, time_per_question,
          max_students, num_variants, vector_store_id, allowed_students[])
materials (id, project_id, file_name, file_path, openai_file_id, status)
questions (id, project_id, variant_number, type, text, points, options[],
           correct_answer, correct_answers[], matching_pairs)
tests (id, project_id, student_id, variant_number, status, score, max_score)
answers (id, test_id, question_id, answer, is_correct, score, ai_grading_details)
participants (id, teacher_id, email, confirmation_status, student_user_id)
```

**Миграции:** 11 штук в `backend/alembic/versions/` (011 — добавлен `is_verified`)

---

## 🔌 Основные API Endpoints

### Auth `/api/v1/auth`

- `POST /register` — регистрация → возвращает `access_token` в body + `refresh_token` в **httpOnly cookie**
- `POST /login` — вход (form-data) → та же схема
- `POST /refresh` — тихое обновление токена через cookie (body не нужен)
- `POST /logout` — удаляет cookie
- `GET /me` — текущий пользователь
- `POST /verify-email` — подтверждение email 6-значным кодом (требует access token)
- `POST /resend-verification` — повторная отправка кода (rate limit: 1 раз/мин)
- `POST /password-reset/request` — отправить код сброса пароля на email
- `POST /password-reset/confirm` — проверить код и сменить пароль

### Projects `/api/v1/projects`

- `POST /` — создать проект
- `POST /{id}/materials` — привязать материалы
- `POST /{id}/vectorize` — векторизация
- `POST /{id}/generate-tests` — генерация (Celery)
- `GET /{id}/questions?variant=N` — вопросы с фильтром
- `POST /{id}/students/group/{grpId}` — добавить группу

### Student `/api/v1/student`

- `GET /tests/available` — доступные тесты
- `POST /tests/{project_id}/start` — начать тест (назначается случайный вариант)
- `POST /tests/{test_id}/submit` — отправить ответы
- `GET /tests/{test_id}/results` — результаты

---

## ⚠️ Критические баги и их решения

### 1. Falsy Value Bug (correctAnswer = 0)

**Проблема:** `correctAnswer: 0` сохранялось как `null`.

```python
# ❌ НЕПРАВИЛЬНО:
correct_answer = q_data.get("correctAnswer") or q_data.get("correctAnswers")

# ✅ ПРАВИЛЬНО:
correct_answer = q_data.get("correctAnswer")
if correct_answer is None:
    correct_answer = q_data.get("correctAnswers")
```

### 2. DateTime Timezone

Backend хранит naive datetime. Frontend отправляет с timezone:

```python
start_time = data.start_time.replace(tzinfo=None) if data.start_time.tzinfo else data.start_time
```

### 3. SQLAlchemy Multiple Foreign Keys

`Participant` имеет два FK к `User`. Решение:

```python
participants = relationship("Participant", foreign_keys="[Participant.teacher_id]")
```

### 4. JSONB массивы (allowed_students)

SQLAlchemy не детектит in-place изменения. **НЕ МУТИРОВАТЬ!**

```python
# ❌ НЕПРАВИЛЬНО:
project.allowed_students.append(email)

# ✅ ПРАВИЛЬНО:
new_list = list(project.allowed_students)
new_list.append(email)
project.allowed_students = new_list
```

### 5. OpenAI File ID Stale

Файлы удалены из OpenAI панели, но ID в БД. Очистка:

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

### 7. UUID в deps.py (SQLite vs PostgreSQL)

В `get_current_user` `payload.sub` — строка. PostgreSQL делает coercion молча, SQLite падает с `'str' has no attribute 'hex'`. Всегда кастить явно:

```python
from uuid import UUID
user_id = UUID(payload.sub)  # не payload.sub напрямую
```

### 6. i18n символ @

Vue-i18n интерпретирует `@` как linked message. Экранировать: `student{'@'}university.edu`

---

## 🚫 Отклонённые решения и причины

### WebSocket для Lobby

**Отклонено:** Нестабильная работа через Cloudflare Tunnel.  
**Заменено на:** REST polling каждые 10 секунд.

### Prometheus + Grafana (мониторинг)

**Отклонено:** Добавляло 4 сервиса и ~500 строк кода, усложняло контекст для AI.  
**Удалено:** Январь 2026.

### Локальные embeddings (ChromaDB)

**Отклонено:** Сложная настройка, требует GPU.  
**Заменено на:** OpenAI Vector Stores (всё делается на стороне OpenAI).

### Endpoint /projects/{id}/statistics

**Отклонено:** Дублировал данные из `/test-results`.  
**Удалено:** Статистика показывается в LobbyView.

---

## 📊 Статус компонентов

| Компонент         | Статус | Примечание                        |
| ----------------- | ------ | --------------------------------- |
| Auth (JWT)        | ✅     | Access token в памяти, refresh в httpOnly cookie, token rotation |
| Email Verification | ✅    | 6-значный код через Resend, Redis TTL 15 мин |
| Forgot Password   | ✅     | 6-значный код, Redis TTL 10 мин, max 5 попыток |
| AI Generation     | ✅     | Двухшаговый RAG                   |
| Test Variants     | ✅     | До 10 вариантов                   |
| Timer Mode        | ✅     | total / per_question              |
| AI Grading        | ✅     | Essay, short-answer               |
| Score Calculation | ✅     | По варианту                       |
| Options Shuffle   | ✅     | Рандомизация позиций              |

---

## 🔧 Команды разработки

```bash
# Тесты (локально через venv)
cd backend
venv/Scripts/python -m pytest tests/ -v   # Windows
# python -m pytest tests/ -v              # Linux/Mac

# Сборка
docker-compose up -d --build

# Сборка конкретных сервисов
docker-compose up -d --build backend celery_worker nginx

# Миграции
docker exec mentis_backend alembic upgrade head

# Логи генерации (Celery)
docker logs mentis_celery_worker --tail 100

# Логи backend
docker logs mentis_backend --tail 50

# Сброс статуса проекта (если генерация зависла)
docker exec -u postgres mentis_postgres psql -U mentis_admin -d mentis_db \
  -c "UPDATE projects SET status = 'ready' WHERE id = 'PROJECT_UUID';"
```

---

## 📁 Ключевые файлы

### Frontend

- `src/types/index.ts` — TypeScript интерфейсы (включая `isVerified?: boolean`)
- `src/services/api.ts` — Axios instance (`withCredentials: true`, `setApiToken`/`getApiToken`)
- `src/services/auth.service.ts` — auth API (silent refresh без body)
- `src/stores/auth.ts` — Pinia store (токен только в памяти, не localStorage)
- `src/views/LoginView.vue` — **split-screen auth** (login + register в одном компоненте, sliding panel)
- `src/views/EmailVerificationView.vue` — верификация email после регистрации
- `src/views/LobbyView.vue` — управление тестом
- `src/views/TestTakeView.vue` — прохождение теста
- `src/i18n/locales/` — 4 языка (en/ru/ua/pl)

### Backend

- `backend/app/core/config.py` — настройки (включая `RESEND_API_KEY`, `FRONTEND_URL`)
- `backend/app/core/deps.py` — JWT dependency (UUID cast обязателен!)
- `backend/app/services/auth_service.py` — **вся бизнес-логика auth** (register, login, refresh, verify, reset)
- `backend/app/services/email_service.py` — Resend API (httpx)
- `backend/app/services/openai_vectorstore.py` — RAG логика
- `backend/app/services/ai_grading.py` — AI оценка
- `backend/app/tasks/test_tasks.py` — Celery генерация
- `backend/app/api/v1/endpoints/auth.py` — тонкий HTTP-слой (cookies)
- `backend/tests/` — 67 тестов (pytest + fakeredis + aiosqlite)

---

## 💡 Советы для AI-ассистентов

1. **Pydantic v2:** Используй `model_dump()` вместо `.dict()`

2. **SQLAlchemy relationships:** Для lazy-loaded данных используй `selectinload()` в запросах

3. **JSONB массивы:** НЕ мутировать in-place, создавать новый список

4. **Status flow проекта:** `draft` → `generating` → `ready` → `active` → `completed`

5. **Локализация:** При добавлении строк — обновляй все 4 файла (en, ru, ua, pl)

6. **Большие генерации (>15 вопросов):** Автоматически разбиваются на батчи

7. **Логи генерации:** Смотри `mentis_celery_worker`, не `mentis_backend`

8. **Auth — access token:** хранится только в памяти Pinia store (`stores/auth.ts`). `localStorage` не используется. После перезагрузки — silent refresh через httpOnly cookie.

9. **Auth — refresh token:** httpOnly cookie, path `/api/v1/auth`, token rotation при каждом refresh.

10. **Тесты:** запускать через `venv/Scripts/python -m pytest tests/` из папки `backend/`. Зависимости: `pytest`, `pytest-asyncio`, `aiosqlite`, `fakeredis`. Email и Redis замокированы автоматически через `autouse=True` фикстуры в `conftest.py`.

---

## 🚧 TODO

- [ ] Manual override — ручная корректировка AI-оценки
- [ ] Export результатов в Excel/PDF
- [ ] Mobile-friendly UI
- [ ] CI/CD — GitHub Actions с тестами
- [ ] Тесты студенческого flow (start test → submit → score)
- [ ] Google OAuth

---

_Последнее обновление: Май 2026_
