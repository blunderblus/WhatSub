FROM python:3.11-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DJANGO_SETTINGS_MODULE=whatsub.settings
ENV PORT=8000
ENV SECRET_KEY=build-time-placeholder
ENV DEBUG=False

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "whatsub.wsgi", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "180", "--access-logfile", "-"]
