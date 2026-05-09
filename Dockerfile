FROM python:3.11-slim

# =========================
# Environment Variables
# =========================
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# =========================
# System Dependencies
# =========================
RUN apt-get update && apt-get install -y \
    curl \
    apt-transport-https \
    gnupg2 \
    unixodbc-dev \
    gcc \
    g++ \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list | tee /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql17 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# =========================
# Work Directory
# =========================
WORKDIR /app

# =========================
# Install Python deps
# =========================
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# =========================
# Copy Project
# =========================
COPY . /app/

# =========================
# Move into Django project
# =========================
WORKDIR /app/backend

# =========================
# Static files folder
# =========================
RUN mkdir -p staticfiles

# =========================
# Collect static safely (no DB / Redis dependency)
# =========================
RUN DB_ENGINE="django.db.backends.sqlite3" \
    DB_NAME=":memory:" \
    SECRET_KEY="dummy-build-key" \
    python manage.py collectstatic --noinput

# =========================
# IMPORTANT: Use fixed port for Railway Docker
# =========================
EXPOSE 8000

# =========================
# Start Gunicorn (FIXED)
# =========================
CMD ["gunicorn", "backend.wsgi:application", "--bind", "0.0.0.0:8000"]