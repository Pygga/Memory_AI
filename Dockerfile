FROM python:3.11-slim

# Установка системных зависимостей (БЕЗ wkhtmltopdf!)
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libharfbuzz0b \
    libffi-dev \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7 \
    libtiff6 \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

ENV PYTHONPATH=/app

# Копируем зависимости первыми (для кэширования)
COPY pyproject.toml uv.lock ./

# Устанавливаем uv и зависимости
RUN pip install --no-cache-dir uv && \
    uv pip install --system --no-cache -r pyproject.toml

# Копируем код
COPY . .

# Создаём директории
RUN mkdir -p /app/logs /app/static/uploads

# Переменные окружения
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Запуск
CMD ["python", "bot/main.py"]