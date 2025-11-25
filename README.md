# Ашан OMS — учебный проект (Django/DRF)

Курсовой проект по дисциплине «Технологии разработки и защиты баз данных». Система автоматизации онлайн-заказов супермаркета Ашан: каталог, корзина, заказы, отчёты и API.

## Запуск локально
1. Установить зависимости: `python -m venv venv && source venv/bin/activate && pip install -r requirements.txt`.
2. Выполнить миграции и загрузить стартовые данные (если нужны fixtures):
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```
3. Запустить сервер: `python manage.py runserver` и открыть `http://localhost:8000/`.

## Запуск через Docker Compose
```bash
docker-compose up --build
```
Приложение будет доступно по `http://localhost:8000/`.

## Роли и доступ
- **ADMIN** — полный доступ, загрузка CSV, просмотр отчётов.
- **MANAGER** — управление каталогом/отчётами.
- **CUSTOMER** — оформление заказов и личный кабинет.

## API и документация
- OpenAPI схема: `GET /api/schema/`
- Swagger UI: `GET /api/docs/`
- Основные эндпоинты: каталог `/api/products/`, корзина/заказы `/api/orders/`, отчёты `/api/reports/...`.

## Горячие клавиши UI
- `Ctrl+F` — фокус на поиске каталога
- `Ctrl+N` — добавление товара в админке (ADMIN/MANAGER)
- `Ctrl+Shift+O` — открыть корзину
- `Alt+1..4` — быстрый переход: каталог/корзина/профиль/настройки
- `Ctrl+L` — страница входа

## Backup/Restore
В каталоге `scripts/` есть примеры `backup.sh` и `restore.sh` для демонстрации резервного копирования БД (адаптируйте под своё окружение и имя контейнера/БД).

## Тесты
Запуск unit-тестов API и проверок безопасности:
```bash
python manage.py test
```
