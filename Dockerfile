FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

WORKDIR /app

COPY pyproject.toml README.md ./
COPY human_ai ./human_ai
COPY config.cloud.json ./config.cloud.json

RUN pip install --no-cache-dir .

EXPOSE 8080

CMD ["sh", "-c", "python -m human_ai.gima --config config.cloud.json web --host 0.0.0.0 --port ${PORT:-8080}"]
