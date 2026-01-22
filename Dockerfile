FROM python:3.12-slim

# Install system dependencies for WeasyPrint and Fonts
# Fixed package names for newer Debian versions
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    python3-cffi \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    libxml2-dev \
    libxslt1-dev \
    fontconfig \
    fonts-noto-core \
    fonts-noto-cjk \
    fonts-noto-ui-extra \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Poetry
RUN pip install poetry
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Copy project files
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=config.settings
ENV SECRET_KEY=build-time-secret-key-only

# Ensure font cache is updated for WeasyPrint to see the fonts
RUN fc-cache -fv

# Collect static files
RUN python manage.py collectstatic --noinput

EXPOSE 8000

# CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]