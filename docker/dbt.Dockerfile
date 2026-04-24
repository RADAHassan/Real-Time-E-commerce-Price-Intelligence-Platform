FROM python:3.11-slim

WORKDIR /dbt

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir dbt-bigquery==1.8.0

COPY dbt_project/ .

ENTRYPOINT ["dbt"]
