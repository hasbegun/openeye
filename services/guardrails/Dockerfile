FROM python:3.12-slim AS base

WORKDIR /app

RUN adduser --disabled-password --gecos "" appuser

COPY services/guardrails/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ /app/shared/
COPY services/guardrails/app/ /app/app/

USER appuser

CMD ["python", "-m", "app.main"]
