FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Системные зависимости (для psycopg2, Pillow и т.п.)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Ставим зависимости
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . /app/

ENV DJANGO_SETTINGS_MODULE=ashan_oms.settings

# (опционально) сбор статики, можно оставить, даже если её почти нет
RUN python manage.py collectstatic --noinput || true

CMD ["gunicorn", "ashan_oms.wsgi:application", "--bind", "0.0.0.0:8000"]
