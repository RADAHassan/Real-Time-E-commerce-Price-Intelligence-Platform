# Architecture — Real-Time E-commerce Price Intelligence Platform

## Overview

This platform monitors e-commerce prices in real-time and in batch using a hybrid
Lambda-style architecture: streaming events flow through Apache NiFi, while
daily batch jobs are orchestrated by Apache Airflow. All data lands in Google
Cloud Bigtable (time-series optimised storage), is transformed by dbt via BigQuery
external tables, and served through a Streamlit dashboard.

---

## Full Data Flow

```mermaid
flowchart TD
    subgraph Scraping["🕷️ Scraping Layer"]
        S1[Scrapy Spider\nbooks.toscrape.com]
        S2[Scrapy Spider\nquotes.toscrape.com]
    end

    subgraph Streaming["⚡ Streaming — Apache NiFi"]
        N1[ListenHTTP\nProcessor]
        N2[JoltTransformJSON\nProcessor]
        N3[PutBigtable\nProcessor]
        N1 --> N2 --> N3
    end

    subgraph Batch["🗓️ Batch — Apache Airflow"]
        A1[DAG: daily_full_scrape]
        A2[DAG: dbt_transformations]
        A3[DAG: weekly_stats_report]
    end

    subgraph Storage["🗄️ Storage — Google Cloud Bigtable"]
        BT[(Bigtable\nprice_table\nrow_key: product_id#rev_ts)]
    end

    subgraph Transform["🔄 Transformations — dbt + BigQuery"]
        D1[staging\nraw cleaning]
        D2[intermediate\njoins + enrichment]
        D3[marts\nKPIs + aggregates]
        D1 --> D2 --> D3
    end

    subgraph Analytics["📊 Analytics — Python"]
        AN1[Notebook 1\nDescriptive Stats]
        AN2[Notebook 2\nInferential Stats]
        AN3[Reports\nHTML / PDF]
        AN1 --> AN3
        AN2 --> AN3
    end

    subgraph Dashboard["🖥️ Streamlit Dashboard"]
        DB1[Page 1: Live Prices]
        DB2[Page 2: Historical KPIs]
        DB3[Page 3: Statistical Results]
        DB4[Page 4: Price Alerts]
    end

    subgraph Monitoring["📈 Monitoring"]
        P[Prometheus]
        G[Grafana]
        P --> G
    end

    S1 -->|HTTP POST JSON| N1
    S2 -->|HTTP POST JSON| N1
    N3 -->|write rows| BT

    A1 -->|trigger spiders| S1
    A1 -->|trigger spiders| S2
    A2 -->|dbt run| D1
    A3 -->|papermill| AN1
    A3 -->|papermill| AN2

    BT -->|external table| D1
    D3 -->|read| Dashboard
    BT -->|direct read| DB1
    BT -->|alerts| DB4
    AN3 -->|embed| DB3

    Streaming --> Monitoring
    Batch --> Monitoring
```

---

## Component Details

### Row Key Design (Bigtable)

```
product_id#reversed_timestamp
Example: books_0001#9999999999999-1745000000000
```

Using a reversed timestamp ensures the most recent data is at the top of
each row group, which optimises range scans for "latest N prices".

### Column Families

| Family | Columns | TTL |
|---|---|---|
| `price_cf` | `current_price`, `original_price`, `currency`, `discount_pct` | 90 days |
| `metadata_cf` | `title`, `category`, `rating`, `url`, `source` | forever |
| `agg_cf` | `avg_7d`, `avg_30d`, `min_30d`, `max_30d`, `volatility` | 30 days |

### dbt Model Layers

```
staging/
  stg_bigtable_prices.sql        -- raw → typed, renamed columns
  stg_bigtable_metadata.sql

intermediate/
  int_prices_with_metadata.sql   -- join price + metadata
  int_daily_price_stats.sql      -- daily aggregates per product

marts/
  mart_price_kpis.sql            -- final KPI table for dashboard
  mart_price_alerts.sql          -- products with >5% change in 24h
  mart_category_comparison.sql   -- cross-category stats
```

---

## Infrastructure (GCP — Phase 9)

```mermaid
flowchart LR
    subgraph GCP["Google Cloud Platform"]
        BT2[(Bigtable\nInstance)]
        BQ[(BigQuery\nDataset)]
        CC[Cloud Composer\nAirflow managed]
        AR[Artifact Registry\nDocker images]
        IAM[IAM\nService Accounts]
    end

    subgraph Local["Local / GitHub Actions"]
        TF[Terraform]
        GH[GitHub Actions CI/CD]
    end

    TF -->|provision| BT2
    TF -->|provision| BQ
    TF -->|provision| CC
    TF -->|provision| AR
    TF -->|manage| IAM
    GH -->|push images| AR
    GH -->|deploy| CC
```

---

## Phase Roadmap

| Phase | Description | Status |
|---|---|---|
| 0 | Bootstrap — repo structure, Docker skeleton | ✅ Done |
| 1 | Scrapy spiders (books + quotes) | ⬜ |
| 2 | Bigtable emulator + schema | ⬜ |
| 3 | NiFi streaming ingestion | ⬜ |
| 4 | Airflow batch orchestration | ⬜ |
| 5 | dbt transformations | ⬜ |
| 6 | Statistical analytics notebooks | ⬜ |
| 7 | Streamlit dashboard | ⬜ |
| 8 | DataOps: CI/CD, GE, Prometheus | ⬜ |
| 9 | GCP deployment (Terraform) | ⬜ |
| 10 | Final deliverables + demo | ⬜ |
