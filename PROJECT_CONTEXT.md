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
users (id, email, password_hash, role, first_name, last_name)
projects (id, teacher_id, title, status, timer_mode, total_time, time_per_question,
          max_students, num_variants, vector_store_id, allowed_students[])
materials (id, project_id, file_name, file_path, openai_file_id, status)
questions (id, project_id, variant_number, type, text, points, options[],
           correct_answer, correct_answers[], matching_pairs)
tests (id, project_id, student_id, variant_number, status, score, max_score)
answers (id, test_id, question_id, answer, is_correct, score, ai_grading_details)
participants (id, teacher_id, email, confirmation_status, student_user_id)
```

**Миграции:** 10 штук в `backend/alembic/versions/`

---

## 🔌 Основные API Endpoints

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
| Auth (JWT)        | ✅     | Access 4h (refresh не реализован) |
| AI Generation     | ✅     | Двухшаговый RAG                   |
| Test Variants     | ✅     | До 10 вариантов                   |
| Timer Mode        | ✅     | total / per_question              |
| AI Grading        | ✅     | Essay, short-answer               |
| Score Calculation | ✅     | По варианту                       |
| Options Shuffle   | ✅     | Рандомизация позиций              |

---

## 🔧 Команды разработки

```bash
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

- `src/types/index.ts` — TypeScript интерфейсы
- `src/services/` — API сервисы
- `src/stores/` — Pinia stores
- `src/views/LobbyView.vue` — управление тестом
- `src/views/TestTakeView.vue` — прохождение теста
- `src/i18n/locales/` — 4 языка

### Backend

- `backend/app/core/config.py` — настройки
- `backend/app/services/openai_vectorstore.py` — RAG логика
- `backend/app/services/ai_grading.py` — AI оценка
- `backend/app/tasks/test_tasks.py` — Celery генерация
- `backend/app/api/v1/endpoints/` — REST endpoints

---

## 💡 Советы для AI-ассистентов

1. **Pydantic v2:** Используй `model_dump()` вместо `.dict()`

2. **SQLAlchemy relationships:** Для lazy-loaded данных используй `selectinload()` в запросах

3. **JSONB массивы:** НЕ мутировать in-place, создавать новый список

4. **Status flow проекта:** `draft` → `generating` → `ready` → `active` → `completed`

5. **Локализация:** При добавлении строк — обновляй все 4 файла (en, ru, ua, pl)

6. **Большие генерации (>15 вопросов):** Автоматически разбиваются на батчи

7. **Логи генерации:** Смотри `mentis_celery_worker`, не `mentis_backend`

---

## 🚧 TODO

- [ ] Manual override — ручная корректировка AI-оценки
- [ ] Export результатов в Excel/PDF
- [ ] Email уведомления
- [ ] Mobile-friendly UI

---

_Последнее обновление: Январь 2026_
