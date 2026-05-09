FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies and Microsoft SQL Server ODBC Driver 17
# This is required for mssql-django to connect to your SQL Server setup
RUN apt-get update && apt-get install -y \
    curl \
    apt-transport-https \
    gnupg2 \
    unixodbc-dev \
    gcc \
    g++ \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql17 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project files
COPY . /app/

# Expose port (default 8000, can be overridden by PORT env var)
EXPOSE 8000

# Change directory to where manage.py is located
WORKDIR /app/backend

# Create staticfiles directory for WhiteNoise
RUN mkdir -p staticfiles

# Collect static files safely without connecting to live SQL database
# We pass a dummy sqlite3 config and dummy secret key so Django builds static files offline securely
RUN DB_ENGINE="django.db.backends.sqlite3" DB_NAME=":memory:" SECRET_KEY="dummy-build-key" python manage.py collectstatic --noinput

# Command to run gunicorn (Railway handles the PORT environment variable)
# Explicitly omitting any database migrations commands to protect live SQL Server schema
CMD gunicorn backend.wsgi:application --bind 0.0.0.0:${PORT:-8000}