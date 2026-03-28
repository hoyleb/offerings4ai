FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY wheels_linux /app/wheels_linux
COPY wheels_linux_amd64 /app/wheels_linux_amd64
COPY requirements.txt /app/
RUN arch="$(python -c 'import platform; print(platform.machine())')" && \
    if [ "${arch}" = "aarch64" ] || [ "${arch}" = "arm64" ]; then \
      pip install --no-index --find-links=/app/wheels_linux -r requirements.txt; \
    else \
      pip install --no-index --find-links=/app/wheels_linux_amd64 -r requirements.txt; \
    fi

COPY app /app/app

EXPOSE 8899 8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8899}"]
