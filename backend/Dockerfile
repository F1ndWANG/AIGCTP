FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.12-slim AS runtime
WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --create-home app

ENV PATH=/root/.local/bin:$PATH PYTHONUNBUFFERED=1

COPY --from=builder /root/.local /root/.local
COPY alembic.ini alembic/ ./alembic/
COPY app/ ./app/
COPY run.py .

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--proxy-headers", "--forwarded-allow-ips", "*"]
