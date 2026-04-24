FROM python:3.12-slim

WORKDIR /app

# System deps (grpc needs these)
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Only the packages the sink needs — keeps the image small
COPY requirements.txt .
RUN pip install --no-cache-dir \
        fastapi \
        uvicorn[standard] \
        google-cloud-bigtable \
        pydantic \
        python-dotenv \
        google-auth

# Copy only the modules required by the sink (no scrapers, no dbt, etc.)
COPY bigtable/ ./bigtable/
COPY sink/     ./sink/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8087

HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8087/health')"

CMD ["uvicorn", "sink.app:app", "--host", "0.0.0.0", "--port", "8087", "--workers", "2"]
