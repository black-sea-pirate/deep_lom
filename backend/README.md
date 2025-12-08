# AI Test Platform Backend

## Структура проекта

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── auth.py         # Аутентификация
│   │       │   ├── projects.py     # Проекты/тесты
│   │       │   ├── materials.py    # Материалы и папки
│   │       │   ├── participants.py # Участники и группы
│   │       │   ├── tests.py        # Тесты и генерация
│   │       │   └── student.py      # Студенческие функции
│   │       └── router.py
│   ├── core/
│   │   ├── config.py    # Настройки приложения
│   │   ├── security.py  # JWT и хеширование
│   │   └── deps.py      # FastAPI зависимости
│   ├── db/
│   │   ├── base.py      # SQLAlchemy Base
│   │   └── session.py   # Сессии БД
│   ├── models/          # SQLAlchemy модели
│   │   ├── user.py
│   │   ├── project.py
│   │   ├── material.py
│   │   ├── participant.py
│   │   ├── test.py
│   │   └── student_email.py
│   ├── schemas/         # Pydantic схемы
│   │   ├── user.py
│   │   ├── project.py
│   │   ├── material.py
│   │   ├── participant.py
│   │   ├── test.py
│   │   └── student.py
│   ├── services/        # Бизнес-логика
│   │   ├── rag.py           # RAG с ChromaDB
│   │   ├── document_processor.py  # Обработка документов
│   │   └── ai_generator.py  # Генерация тестов GPT-4.1
│   ├── tasks/           # Celery задачи
│   │   ├── document_tasks.py
│   │   └── test_tasks.py
│   ├── celery_app.py    # Конфиг Celery
│   └── main.py          # FastAPI приложение
├── Dockerfile
├── requirements.txt
└── .env
```

## Быстрый старт (локально)

### 1. Запуск инфраструктуры (Docker)

```bash
# Из корня проекта
docker-compose up -d postgres redis chromadb
```

### 2. Установка зависимостей

```bash
cd backend
python -m venv venv
source venv/bin/activate  # или venv\Scripts\activate на Windows
pip install -r requirements.txt
```

### 3. Настройка .env

```bash
cp .env.example .env
# Отредактируйте .env, добавьте OPENAI_API_KEY
```

### 4. Запуск сервера

```bash
uvicorn app.main:app --reload --port 8000
```

### 5. Запуск Celery воркера

```bash
celery -A app.celery_app worker --loglevel=info --queues=documents,tests
```

## API Документация

После запуска доступна по адресам:

- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

## Основные эндпоинты

### Аутентификация

- `POST /api/v1/auth/register` - Регистрация
- `POST /api/v1/auth/login` - Вход (OAuth2)
- `GET /api/v1/auth/me` - Текущий пользователь
- `POST /api/v1/auth/refresh` - Обновление токена

### Проекты

- `GET /api/v1/projects` - Список проектов
- `POST /api/v1/projects` - Создать проект
- `GET /api/v1/projects/{id}` - Получить проект
- `PUT /api/v1/projects/{id}` - Обновить проект
- `DELETE /api/v1/projects/{id}` - Удалить проект

### Материалы

- `GET /api/v1/materials` - Список материалов
- `POST /api/v1/materials/upload` - Загрузить файл
- `DELETE /api/v1/materials/{id}` - Удалить материал
- `GET /api/v1/materials/folders` - Список папок

### Тесты

- `POST /api/v1/tests/generate` - Генерация через AI
- `GET /api/v1/tests/project/{id}` - Тесты проекта
- `POST /api/v1/tests/{id}/submit` - Отправить ответы

## RAG Pipeline

1. **Загрузка документа** → `POST /materials/upload`
2. **Векторизация** → Celery task `process_document`
   - Извлечение текста (PDF, DOCX, TXT, OCR)
   - Разбиение на чанки
   - Создание embeddings (OpenAI)
   - Сохранение в ChromaDB
3. **Генерация теста** → `POST /tests/generate`
   - Поиск релевантных чанков
   - GPT-4.1 генерирует вопросы на основе контекста
   - Минимизация галлюцинаций

## Deployment (Debian)

```bash
# Клонируем репозиторий
git clone https://github.com/black-sea-pirate/deep_lom.git
cd deep_lom

# Настраиваем .env
cp .env.production .env
nano .env  # Заполняем секреты

# Запускаем все сервисы
docker-compose up -d

# Проверяем
docker-compose ps
docker-compose logs -f backend
```
