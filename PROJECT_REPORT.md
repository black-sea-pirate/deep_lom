# AI Test Platform - Отчёт о проделанной работе

## 📋 Описание проекта

**AI Test Platform** — веб-приложение для автоматической генерации персонализированных тестов с использованием языковых моделей (GPT-4.1). Система предназначена для преподавателей и студентов, позволяет создавать тесты на основе загруженных учебных материалов.

### Основная идея

1. Преподаватель загружает учебные материалы (PDF, DOCX, TXT, изображения)
2. AI анализирует материалы и генерирует вопросы разных типов
3. Студенты проходят тесты, система автоматически проверяет ответы
4. Преподаватель получает детальную аналитику по результатам

---

## 🛠 Технологический стек

### Frontend (Реализован ✅)

- **Vue 3** (Composition API, `<script setup>`)
- **TypeScript** — строгая типизация
- **Vite 7.1** — сборка и dev-сервер
- **Element Plus** — UI библиотека
- **Vue Router 4** — маршрутизация с guard'ами
- **Pinia** — state management
- **Vue I18n** — интернационализация (EN, PL, UA, RU)
- **Axios** — HTTP клиент с interceptors
- **SCSS** — стилизация с CSS переменными

### Backend (Планируется 🔜)

- **FastAPI** (Python)
- **PostgreSQL** — основная БД
- **Redis** — кэширование, сессии
- **OpenAI API (GPT-4.1)** — генерация тестов
- **Celery** — фоновые задачи (генерация тестов)
- **JWT** — аутентификация

---

## 📁 Структура Frontend

```
src/
├── assets/                 # Статические ресурсы
├── components/             # Переиспользуемые компоненты
│   └── ThemeToggle.vue     # Переключатель темы
├── i18n/                   # Интернационализация
│   ├── index.ts            # Конфигурация i18n
│   └── locales/            # Файлы переводов
│       ├── en.ts           # English
│       ├── pl.ts           # Polski
│       ├── ua.ts           # Українська
│       └── ru.ts           # Русский
├── layouts/
│   └── TeacherLayout.vue   # Layout с боковым меню для учителя
├── router/
│   └── index.ts            # Маршруты с guards
├── services/               # API сервисы
│   ├── api.ts              # Axios instance с interceptors
│   ├── auth.service.ts     # Авторизация
│   ├── project.service.ts  # Проекты
│   ├── material.service.ts # Материалы
│   ├── participant.service.ts # Участники
│   └── test.service.ts     # Тесты
├── stores/                 # Pinia stores
│   ├── auth.ts             # Авторизация
│   ├── project.ts          # Проекты
│   ├── test.ts             # Тесты
│   └── theme.ts            # Тема (light/dark)
├── styles/
│   └── main.scss           # Глобальные стили, CSS переменные, темы
├── types/
│   └── index.ts            # TypeScript интерфейсы
├── views/                  # Страницы
│   ├── LoginView.vue
│   ├── RegisterView.vue
│   ├── TeacherDashboardView.vue
│   ├── TeacherParticipantsView.vue
│   ├── TeacherMaterialsView.vue
│   ├── TeacherAnalyticsView.vue
│   ├── TeacherSettingsView.vue
│   ├── ProjectCreateView.vue
│   ├── ProjectDetailView.vue
│   ├── ProjectStatisticsView.vue
│   ├── QuestionEditorView.vue
│   ├── LobbyView.vue
│   ├── StudentDashboardView.vue
│   ├── TestTakeView.vue
│   └── TestResultsView.vue
├── App.vue
└── main.ts
```

---

## 🔐 Роли пользователей

### Преподаватель (Teacher)

- Создание и управление проектами (тестами)
- Загрузка учебных материалов в папки
- Управление участниками (студенты, группы)
- Редактирование сгенерированных вопросов
- Просмотр аналитики и статистики
- Проведение тестов (Lobby)

### Студент (Student)

- Просмотр доступных тестов
- Прохождение тестов
- Просмотр результатов

---

## 📄 Реализованные страницы

### Аутентификация

| Страница | Путь        | Описание                              |
| -------- | ----------- | ------------------------------------- |
| Login    | `/login`    | Вход с выбором роли (teacher/student) |
| Register | `/register` | Регистрация нового пользователя       |

### Зона преподавателя (под TeacherLayout)

| Страница        | Путь                              | Описание                          |
| --------------- | --------------------------------- | --------------------------------- |
| Dashboard       | `/teacher`                        | Список проектов, создание нового  |
| Participants    | `/teacher/participants`           | Управление студентами и группами  |
| Materials       | `/teacher/materials`              | Загрузка файлов, папки, drag-drop |
| Analytics       | `/teacher/analytics`              | Статистика, графики, топ студенты |
| Settings        | `/teacher/settings`               | Настройки аккаунта                |
| Project Create  | `/teacher/project/create`         | 4-шаговый wizard создания проекта |
| Project Detail  | `/teacher/project/:id`            | Детали проекта                    |
| Question Editor | `/teacher/project/:id/edit`       | Редактор вопросов                 |
| Lobby           | `/teacher/project/:id/lobby`      | Ожидание студентов перед тестом   |
| Statistics      | `/teacher/project/:id/statistics` | Результаты по проекту             |

### Зона студента

| Страница  | Путь                        | Описание                      |
| --------- | --------------------------- | ----------------------------- |
| Dashboard | `/student`                  | Доступные и завершённые тесты |
| Test Take | `/student/test/:id`         | Прохождение теста             |
| Results   | `/student/test/:id/results` | Результаты теста              |

---

## 📊 TypeScript типы (src/types/index.ts)

### Основные интерфейсы:

```typescript
User; // Пользователь (id, email, role, firstName, lastName)
Project; // Проект/тест (id, title, settings, status, materials, tests)
ProjectSettings; // Настройки (totalTime, timePerQuestion, questionTypes, maxStudents)
Material; // Загруженный файл (id, fileName, fileType, folderId)
MaterialFolder; // Папка для материалов
Participant; // Студент (individual или group-member)
ParticipantGroup; // Группа студентов
Test; // Тест студента (questions, answers, score, status)
Answer; // Ответ на вопрос
```

### Типы вопросов (Question):

- `SingleChoiceQuestion` — один правильный ответ
- `MultipleChoiceQuestion` — несколько правильных ответов
- `TrueFalseQuestion` — правда/ложь
- `ShortAnswerQuestion` — короткий текстовый ответ
- `EssayQuestion` — развёрнутый ответ
- `MatchingQuestion` — сопоставление пар

---

## 🎨 Темы и стили

### CSS переменные (main.scss)

- **Светлая тема** — `:root` (по умолчанию)
- **Тёмная тема** — `.dark` класс на `<html>`

### Переменные:

```scss
--color-primary, --color-secondary, --color-accent
--color-background, --color-surface, --color-border
--color-text, --color-text-light
--spacing-xs/sm/md/lg/xl
--radius-sm/md/lg
--shadow-sm/md/lg
```

### Element Plus Dark Theme

Добавлены переопределения всех Element Plus CSS переменных для тёмной темы:

- `--el-bg-color`, `--el-text-color-*`, `--el-border-color-*`
- Стили для: cards, tables, inputs, menus, dialogs, dropdowns, tags, etc.

---

## 🌐 API Сервисы (готовы к интеграции)

### api.ts — Axios instance

```typescript
- Base URL: VITE_API_URL (http://localhost:8000/api/v1)
- Timeout: 30 секунд
- Request interceptor: JWT token injection
- Response interceptor: 401 → redirect to login, error handling
```

### Сервисы:

| Файл                   | Endpoints                                                                        |
| ---------------------- | -------------------------------------------------------------------------------- |
| auth.service.ts        | login, register, logout, getCurrentUser, refreshToken                            |
| project.service.ts     | getAll, getById, create, update, delete, updateStatus                            |
| material.service.ts    | getAll, upload, delete, getFolders, createFolder, updateFolder, deleteFolder     |
| participant.service.ts | getAll, create, update, delete, getGroups, createGroup, updateGroup, deleteGroup |
| test.service.ts        | generate, getByProject, submit, getResults                                       |

---

## 🔜 Что нужно реализовать на Backend

### 1. Аутентификация

```
POST /api/v1/auth/register    — регистрация
POST /api/v1/auth/login       — вход (возвращает JWT)
POST /api/v1/auth/logout      — выход
GET  /api/v1/auth/me          — текущий пользователь
POST /api/v1/auth/refresh     — обновление токена
```

### 2. Проекты

```
GET    /api/v1/projects           — список проектов преподавателя
POST   /api/v1/projects           — создать проект
GET    /api/v1/projects/:id       — детали проекта
PUT    /api/v1/projects/:id       — обновить проект
DELETE /api/v1/projects/:id       — удалить проект
PATCH  /api/v1/projects/:id/status — изменить статус
```

### 3. Материалы

```
GET    /api/v1/materials              — список материалов
POST   /api/v1/materials/upload       — загрузка файла (multipart/form-data)
DELETE /api/v1/materials/:id          — удалить материал
GET    /api/v1/materials/folders      — список папок
POST   /api/v1/materials/folders      — создать папку
PUT    /api/v1/materials/folders/:id  — обновить папку
DELETE /api/v1/materials/folders/:id  — удалить папку
```

### 4. Участники

```
GET    /api/v1/participants           — список студентов
POST   /api/v1/participants           — добавить студента
PUT    /api/v1/participants/:id       — обновить студента
DELETE /api/v1/participants/:id       — удалить студента
GET    /api/v1/participants/groups    — список групп
POST   /api/v1/participants/groups    — создать группу
PUT    /api/v1/participants/groups/:id — обновить группу
DELETE /api/v1/participants/groups/:id — удалить группу
```

### 5. Тесты и генерация

```
POST /api/v1/tests/generate           — генерация теста через AI
     Body: { projectId, materialIds, settings }

GET  /api/v1/tests/project/:projectId — тесты по проекту
POST /api/v1/tests/:id/submit         — отправить ответы студента
GET  /api/v1/tests/:id/results        — результаты теста
```

### 6. AI интеграция (GPT-4.1)

- Парсинг загруженных материалов (PDF, DOCX, TXT, images с OCR)
- Отправка контента в OpenAI API
- Генерация вопросов разных типов по настройкам
- Сохранение сгенерированных вопросов в БД

---

## 📐 Схема базы данных (рекомендация)

```sql
users (id, email, password_hash, role, first_name, last_name, created_at)

projects (id, teacher_id, title, description, group_name, status,
          total_time, time_per_question, max_students,
          start_time, end_time, created_at)

question_type_configs (id, project_id, type, count)

materials (id, project_id, folder_id, file_name, file_type, file_path, uploaded_at)

material_folders (id, teacher_id, name, description, created_at)

participants (id, teacher_id, email, first_name, last_name, type, group_id, created_at)

participant_groups (id, teacher_id, name, description, created_at)

questions (id, project_id, type, text, points, options, correct_answer, created_at)

tests (id, project_id, student_id, status, score, max_score, started_at, completed_at)

answers (id, test_id, question_id, answer, is_correct, score, feedback)
```

---

## ✅ Чеклист готовности Frontend

- [x] Аутентификация (Login, Register, guards)
- [x] Dashboard преподавателя с проектами
- [x] Wizard создания проекта (4 шага)
- [x] Управление материалами с папками
- [x] Управление участниками (студенты + группы)
- [x] Редактор вопросов (mock)
- [x] Страница Lobby для проведения тестов
- [x] Аналитика и статистика
- [x] Dashboard студента
- [x] Прохождение теста
- [x] Результаты теста
- [x] Тёмная тема (полная поддержка Element Plus)
- [x] Интернационализация (EN, PL, UA, RU)
- [x] API сервисы готовы к интеграции
- [x] Responsive дизайн

---

## 🚀 Запуск проекта

```bash
# Установка зависимостей
npm install

# Dev сервер (http://localhost:5173)
npm run dev

# Production build
npm run build
```

### Environment variables

```env
# .env.development
VITE_API_URL=http://localhost:8000/api/v1
VITE_APP_TITLE=AI Test Platform
```

---

## 📝 Примечания для backend разработки

1. **JWT токен** хранится в `localStorage` под ключом `token`
2. **Axios interceptor** автоматически добавляет `Authorization: Bearer {token}`
3. При **401 ответе** — автоматический редирект на `/login`
4. **Файлы загружаются** через `multipart/form-data` с полем `file`
5. **Тема** хранится в `localStorage` под ключом `theme` ("light" | "dark")
6. **Язык** хранится в `localStorage` под ключом `locale` ("en" | "pl" | "ua" | "ru")

---

## 🔗 Полезные файлы для изучения

1. `src/types/index.ts` — все TypeScript интерфейсы
2. `src/services/api.ts` — конфигурация Axios
3. `src/router/index.ts` — все маршруты
4. `src/stores/` — Pinia stores с mock данными
5. `src/i18n/locales/en.ts` — все ключи переводов

---

## 📝 Обновление от 25.11.2025 (вечер)

### Панель студента (StudentDashboardView.vue) — полная переработка

#### Новый функционал:

1. **Горизонтальное меню в хедере**

   - Кнопка "Dashboard" — переход на главную
   - Кнопка "Моя Статистика" — открывает диалог со статистикой

2. **Переключатели в хедере**

   - ThemeToggle — переключение светлой/тёмной темы
   - Селектор языка (EN/PL/UA/RU)

3. **Кликабельные карточки статистики**

   - "Всього Тестів" → диалог с описанием
   - "Середній Бал" → диалог с прогресс-баром
   - "Завершені Тести" → таблица пройденных тестов с результатами

4. **Меню аккаунта (dropdown)**

   - **Управление email**:
     - Список email с привязкой к учреждениям
     - Добавление новых email (для разных курсов/учебных заведений)
     - Установка основного email
     - Удаление неосновных email
   - **Смена пароля**:
     - Форма с валидацией (мин. 6 символов, совпадение паролей)

5. **Исправлена тёмная тема**
   - Header теперь использует CSS переменные

#### Новые переводы (все 4 языка):

```typescript
// Добавлены секции:
studentAccount: {
  manageEmails,
    changePassword,
    yourEmails,
    emailsHint,
    primary,
    makePrimary,
    addNewEmail,
    addEmail,
    institution,
    emailPlaceholder,
    institutionPlaceholder,
    emailAdded,
    emailRemoved,
    primaryChanged,
    confirmRemoveEmail,
    cannotRemovePrimary,
    invalidEmail,
    currentPassword,
    newPassword,
    confirmNewPassword,
    passwordChanged,
    passwordMismatch,
    passwordTooShort;
}

studentStats: {
  totalDescription, averageDescription, testName, course, date;
}
```

#### Бизнес-логика для backend:

```
# Новые endpoints для студента:

# Email management
GET    /api/v1/student/emails           — список email студента
POST   /api/v1/student/emails           — добавить email
DELETE /api/v1/student/emails/:id       — удалить email
PATCH  /api/v1/student/emails/:id/primary — сделать основным

# Password
POST   /api/v1/student/change-password  — сменить пароль
       Body: { currentPassword, newPassword }

# Statistics
GET    /api/v1/student/statistics       — статистика студента
GET    /api/v1/student/tests/completed  — список пройденных тестов
```

#### TypeScript типы для backend:

```typescript
// Добавить в types/index.ts

interface StudentEmail {
  id: string;
  email: string;
  isPrimary: boolean;
  institution: string;
  createdAt: Date;
}

interface ChangePasswordRequest {
  currentPassword: string;
  newPassword: string;
}

interface StudentStatistics {
  totalTests: number;
  completedTests: number;
  averageScore: number;
}

interface CompletedTest {
  id: string;
  title: string;
  groupName: string;
  score: number;
  maxScore: number;
  completedAt: Date;
}
```

---

_Отчёт составлен: 25 ноября 2025_
_Последнее обновление: 25 ноября 2025 (вечер)_
_Frontend версия: 0.0.0 (pre-release)_
