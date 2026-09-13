ARG PYTHON_VERSION=3.12-slim
FROM python:${PYTHON_VERSION}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_PATH=/data/bridge.db \
    LOGO_PATH=/data/branding/logo

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY server ./server

RUN mkdir -p /data && chown -R nobody:nogroup /data /app

USER nobody

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--threads", "4", "--timeout", "30", "--access-logfile", "-", "--error-logfile", "-", "server.app:app"]
