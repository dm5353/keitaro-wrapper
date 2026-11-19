# Keitaro Wrapper (Campaign Creator & Streams Editor)

Веб-приложение на **FastAPI + SQLAlchemy** для автоматизации работы с трекером **Keitaro** через Admin API.

## Функциональность

1. **Создаватор кампаний:**
   - Валидация префикса имени (`test_фамилия_...`).
   - Поддержка списка ГЕО через запятую (`MX,AU,RO`).
   - Поиск офферов с автокомплитом.
   - Автоматическое создание кампании с двумя потоками:
     - **Поток 1:** перехват указанных стран и редирект на `https://google.com`.
     - **Поток 2:** направление остального трафика на выбранный оффер.
   - Автоматический откат (удаление кампании) при сбое создания потоков.

2. **Редактор существующей кампании:**
   - Загрузка актуальных потоков и офферов кампании из Keitaro (`FETCH STREAMS FROM KT`).
   - Добавление (`ADD`) и отключение (`REMOVE` / `BRING BACK`) офферов в режиме черновика.
   - Автоматический пересчёт долей (`Share`) до 100% с поддержкой закрепления доли (`📌`) и ручного ввода процентов.
   - Отправка изменений в трекер по кнопке `PUSH TO KT` и сброс черновика по кнопке `CANCEL`.
   - Сохранение истории удалённых офферов в локальной БД (включая офферы, удалённые напрямую в админке Keitaro).

## Стек технологий

- **Backend:** Python 3.11+, FastAPI, httpx, Pydantic
- **База данных и миграции:** SQLAlchemy (Async), SQLite (`aiosqlite`), Alembic
- **Frontend:** HTML, CSS, Vanilla JavaScript

---

## Установка и запуск

### 1. Клонирование репозитория и создание виртуального окружения

```bash
git clone https://github.com/dm5353/keitaro-wrapper
cd keitaro-wrapper

python -m venv venv
# Для Windows:
venv\Scripts\activate
# Для Linux/macOS:
source venv/bin/activate
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Настройка переменных окружения

Скопируйте шаблон `.env.example` в `.env` и заполните своими данными:

```bash
# Для Windows:
copy .env.example .env
# Для Linux/macOS:
cp .env.example .env
```

Отредактируйте `.env`:
```env
KEITARO_URL=https://ваш-домен-трекера.com
KEITARO_API_KEY=ваш_секретный_ключ_из_настроек_keitaro
DATABASE_URL=sqlite+aiosqlite:///./keitaro_app.db
```

### 4. Применение миграций базы данных (Alembic)

Перед первым запуском создайте таблицы локальной базы данных:

```bash
alembic upgrade head
```

### 5. Запуск сервера

```bash
uvicorn app.main:app --reload
```

После запуска интерфейс будет доступен по адресу: **http://127.0.0.1:8000**
