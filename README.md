# 🎓 Mentis — AI Test Generation Platform

> Веб-платформа для автоматической генерации персонализированных тестов с использованием GPT-4.1 и OpenAI Vector Stores (RAG)

## 📋 О проекте

**Mentis** — дипломный fullstack проект, помогающий преподавателям создавать уникальные тесты на основе учебных материалов с AI-оценкой ответов студентов.

**🌐 Production:** https://mentis.forzone.uk  
**API Docs:** https://mentis.forzone.uk/api/docs

## ✨ Возможности

### Для преподавателей

- Wizard создания проектов (4 шага)
- Загрузка материалов (PDF, DOCX, TXT)
- Генерация N уникальных вариантов теста (защита от списывания)
- Два режима таймера: общий / на вопрос
- Редактор вопросов с фильтрацией по вариантам
- Lobby для управления тестом
- AI-оценка эссе и коротких ответов

### Для студентов

- Dashboard с предстоящими тестами
- Обратный отсчёт до начала
- Интерфейс прохождения теста
- Просмотр результатов с feedback

### Типы вопросов

- Single Choice / Multiple Choice
- True/False
- Short Answer (AI grading)
- Essay (AI grading)
- Matching

## 🛠 Технологический стек

| Layer              | Technologies                                                                     |
| ------------------ | -------------------------------------------------------------------------------- |
| **Frontend**       | Vue 3, TypeScript, Vite, Element Plus, Pinia, Vue Router, Vue I18n (en/pl/ua/ru) |
| **Backend**        | FastAPI 0.115, Python 3.11, SQLAlchemy 2.0 async, Pydantic v2, Celery            |
| **Database**       | PostgreSQL 16, Redis 7                                                           |
| **AI/RAG**         | OpenAI GPT-4.1, Vector Stores, двухшаговый RAG                                   |
| **Infrastructure** | Docker Compose (6 сервисов), Nginx, Cloudflare Tunnel                            |

## 🚀 Быстрый старт

### Требования

- Docker & Docker Compose
- OpenAI API Key
- Cloudflare Tunnel Token (для production)

### Запуск

```bash
# Клонирование
git clone https://github.com/black-sea-pirate/deep_lom.git
cd deep_lom

# Настройка
cp .env.example .env
# Отредактируйте .env: OPENAI_API_KEY, CLOUDFLARE_TUNNEL_TOKEN

# Запуск всех сервисов
docker-compose up -d --build

# Проверка
docker ps
```

### Локальная разработка (Frontend)

```bash
npm install
npm run dev
# Открыть http://localhost:5173
```

## 📁 Структура проекта

```
mentis/
├── src/                    # Vue 3 Frontend
│   ├── views/              # Страницы (Login, Dashboard, Lobby, TestTake...)
│   ├── services/           # API сервисы
│   ├── stores/             # Pinia stores
│   ├── i18n/locales/       # 4 языка
│   └── types/              # TypeScript типы
├── backend/
│   ├── app/
│   │   ├── api/v1/         # REST endpoints
│   │   ├── models/         # SQLAlchemy модели
│   │   ├── services/       # AI генерация, RAG
│   │   └── tasks/          # Celery задачи
│   └── alembic/            # 10 миграций БД
├── docker-compose.yml      # 6 сервисов
└── nginx.conf
```

## 🐳 Docker сервисы

| Сервис          | Назначение                             |
| --------------- | -------------------------------------- |
| `postgres`      | PostgreSQL 16 — база данных            |
| `redis`         | Redis 7 — Celery broker + кэш          |
| `backend`       | FastAPI приложение                     |
| `celery_worker` | Фоновые задачи (генерация, AI grading) |
| `nginx`         | Frontend + reverse proxy               |
| `cloudflared`   | HTTPS через Cloudflare Tunnel          |

## 🔧 Полезные команды

```bash
# Пересборка
docker-compose up -d --build backend celery_worker nginx

# Миграции
docker exec mentis_backend alembic upgrade head

# Логи
docker logs mentis_backend --tail 50
docker logs mentis_celery_worker --tail 100

# Статус
docker ps
```

## 🌍 Поддержка языков

- 🇬🇧 English
- 🇵🇱 Polski
- 🇺🇦 Українська
- 🇷🇺 Русский

## 📄 Лицензия

Дипломный проект. Все права защищены.

---

**Статус:** 🟢 Production  
**Последнее обновление:** Январь 2026
