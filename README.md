# Real-Time E-commerce Price Intelligence Platform

> End-to-end hybrid batch + streaming data engineering platform for e-commerce price monitoring.
> Final-year academic project — Hassan RADA · 2025-2026

---

## What This Project Does

This platform continuously scrapes product prices from 5 e-commerce websites, processes them through a multi-layer data pipeline, stores them in a time-series database, transforms them with dbt, runs statistical analysis, and displays everything in a live interactive dashboard.

**Live demo:** `python3 -m streamlit run dashboard/app.py` → http://localhost:8501

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                                 │
│  books.toscrape.com · scrapeme.live · jumia.ma · ultrapc.ma        │
│  micromagma.ma                                                      │
└──────────────────────────┬──────────────────────────────────────────┘
                           │  Scrapy spiders
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     INGESTION LAYER                                 │
│                                                                     │
│  ┌─────────────────┐    ┌──────────────────┐    ┌───────────────┐  │
│  │  Apache Kafka   │    │   Apache NiFi    │    │  JSONL files  │  │
│  │  (streaming)    │    │  (HTTP routing)  │    │  (fallback)   │  │
│  └────────┬────────┘    └────────┬─────────┘    └───────┬───────┘  │
│           └─────────────────────┴─────────────────────  │          │
└─────────────────────────────────┬───────────────────────┘──────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      STORAGE LAYER                                  │
│                                                                     │
│         Google Cloud Bigtable  (time-series, row key:              │
│         source#product_id#timestamp)                                │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │  Apache Airflow (batch scheduler)
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   TRANSFORMATION LAYER                              │
│                                                                     │
│   dbt-bigquery                                                      │
│   ├── staging/      raw → cleaned, typed, deduped                  │
│   ├── intermediate/ joins + price change calculations               │
│   └── marts/        mart_price_stats · mart_price_history           │
│                     mart_price_alerts · mart_current_prices         │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ANALYTICS LAYER                                  │
│                                                                     │
│   Jupyter notebooks (SciPy, statsmodels, Plotly)                   │
│   ├── 01_descriptive_stats.ipynb                                    │
│   │    mean/median/mode, IQR, skewness, Shapiro-Wilk, outliers     │
│   └── 02_inferential_stats.ipynb                                    │
│        ANOVA, Kruskal-Wallis, Mann-Whitney, regression, CI          │
│                                                                     │
│   analytics/validate_data.py  (18 Great-Expectations-style checks)  │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  PRESENTATION LAYER                                 │
│                                                                     │
│   Streamlit dashboard  (67,000 products, 4 pages)                  │
│   ├── Live Feed     — real-time price table + filters               │
│   ├── Analytics     — KPI cards + trend explorer                    │
│   ├── Statistics    — hypothesis tests + regression                 │
│   └── Alerts        — price drop detection                          │
│                                                                     │
│   FastAPI  REST API  (BigQuery read path)                           │
│   React    SPA frontend  (served by Nginx)                          │
└─────────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────────────────────────────────────────┐
│                  OBSERVABILITY                                       │
│   Prometheus  metrics scraping · Grafana  pre-built dashboard       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Scraping | Scrapy + BeautifulSoup | 2.x |
| Streaming | Apache Kafka | 7.6 (Confluent) |
| HTTP Routing | Apache NiFi | 1.25 |
| Orchestration | Apache Airflow | 2.9 |
| Storage | Google Cloud Bigtable (emulator) | SDK 2.x |
| SQL transforms | dbt-bigquery | 1.7 |
| Analytics | Python · SciPy · statsmodels · Pandas · NumPy | — |
| Dashboard | Streamlit · Plotly | — |
| API | FastAPI | 0.111 |
| Frontend | React + Nginx | 18 |
| Infrastructure | Docker Compose · Terraform · Kubernetes | — |
| CI/CD | GitHub Actions | — |
| Data Quality | Custom GE-style validation (18 checks) | — |
| Monitoring | Prometheus 2.51 · Grafana 10.4 | — |

---

## Project Structure

```
price-intelligence-platform/
│
├── scrapers/                  Scrapy project
│   ├── spiders/               5 spiders (one per site)
│   ├── pipelines.py           Validation → JSONL → Kafka → NiFi → Bigtable
│   ├── middlewares.py         User-agent rotation
│   └── settings.py            Rate limiting, retry, pipeline config
│
├── kafka/
│   ├── producer.py            Streams JSONL data → 'price.raw' topic
│   └── consumer.py            Reads 'price.raw' → data/kafka_stream/stream.jsonl
│
├── nifi/
│   ├── templates/             NiFi flow XML templates
│   └── scripts/               REST API deployment scripts
│
├── airflow/
│   ├── dags/                  3 DAGs: daily scrape, dbt run, weekly report
│   └── plugins/               Custom operators
│
├── bigtable/
│   ├── client.py              BigtableClient with schema helpers
│   └── setup_tables.py        Table + column family creation
│
├── sink/
│   └── app.py                 FastAPI microservice: NiFi → Bigtable HTTP bridge
│
├── dbt_project/
│   ├── models/
│   │   ├── staging/           stg_prices — raw cleaning + typing
│   │   ├── intermediate/      int_price_changes — LAG + pct change
│   │   └── marts/             mart_price_stats, mart_price_history,
│   │                          mart_price_alerts, mart_current_prices
│   ├── tests/                 Custom dbt tests
│   └── macros/                Reusable SQL macros
│
├── analytics/
│   ├── notebooks/
│   │   ├── 01_descriptive_stats.ipynb
│   │   └── 02_inferential_stats.ipynb
│   ├── validate_data.py       18-check data quality CLI
│   └── reports/               Auto-generated HTML reports
│
├── dashboard/
│   ├── app.py                 Streamlit dashboard (4 pages, dark UI)
│   └── data_loader.py         Bigtable → BigQuery → JSONL priority chain
│
├── data/
│   └── demo/
│       └── demo_products.jsonl  67,000 synthetic products (14.5 MB)
│
├── scripts/
│   └── generate_demo_data.py  Generates the 67K demo dataset
│
├── api/                       FastAPI read-path (BigQuery mart tables)
├── frontend/                  React SPA
│
├── docker/
│   ├── airflow.Dockerfile
│   ├── sink.Dockerfile
│   ├── dashboard.Dockerfile
│   ├── api.Dockerfile
│   ├── frontend.Dockerfile
│   ├── prometheus.yml         Scrape configs
│   └── grafana/
│       ├── provisioning/      Auto-provision datasource + dashboard
│       └── dashboards/        price_intelligence.json
│
├── infra/terraform/           GCP: Bigtable + BigQuery + Cloud Run
├── .github/workflows/         CI: lint + test + Docker build
└── tests/                     Unit + integration tests
```

---

## The Dashboard — 4 Pages

### Page 1 — Live Feed
- Loads all 67,000 products in ~0.7 seconds
- **Source filter** — pill buttons colored per source (Books=indigo, Jumia=orange, etc.)
- **Availability filter** — dropdown (In stock / N available / Out of stock / Pre-order)
- **Price range slider** — min/max bounds
- **Search** — full-text on title + category
- **Sort chips** — Price ↑, Price ↓, Rating ↓, Name A→Z
- **KPI strip** — Products, Sources, Avg price, Lowest, Highest
- **Violin chart** — price distribution per source (log scale)
- **Donut chart** — market share by source
- **Progress bars** — volume per source
- **Data table** — paginated, sortable, typed columns

### Page 2 — Analytics
- Per-source KPI cards (avg, median, σ)
- Grouped bar chart (Min / Avg / Median / Max per source)
- Volume progress bars per source
- **Trend explorer** — select any product, view price over time, highlight drops ≥5%

### Page 3 — Statistics
Three tabs:
- **Descriptive** — mean, median, std, IQR, skewness, kurtosis; distribution histogram; CV% bar chart; box plots
- **Hypothesis tests** — Shapiro-Wilk normality; one-way ANOVA (F-statistic, η²); Kruskal-Wallis (H-statistic, ε²); pairwise Mann-Whitney U with effect size r; p-value heatmap; 95% CI forest plot
- **Regression** — price ~ rating OLS scatter with trendline; slope β₁, intercept β₀, R², p-value; per-source regression table

### Page 4 — Alerts
- Detects price drops ≥5% using LAG comparison across scrape sessions
- Severity threshold slider (−5% to −50%)
- KPI strip: total alerts, biggest drop, sources hit, severe (≥20%)
- Alert cards with left-accent color (yellow=mild, orange=moderate, red=severe)
- Horizontal bar chart of top 20 drops
- Severity donut chart

---

## The 67,000 Demo Products

Generated by `scripts/generate_demo_data.py`:

| Source | Count | Currency | Category examples | Price range |
|---|---|---|---|---|
| books_toscrape | 20,000 | GBP | Mystery, Sci-Fi, Romance, History, Poetry… (48 genres) | £1 – £60 |
| scrapeme_live | 11,000 | GBP | Fruits & Veg, Dairy, Bakery, Beverages, Snacks… | £0.49 – £50 |
| jumia_ma | 20,000 | MAD | Smartphones, Fashion, Appliances, Sports, Baby… | 30 – 25,000 MAD |
| ultrapc_ma | 8,000 | MAD | CPUs, GPUs, RAM, SSDs, Monitors, Peripherals… | 80 – 30,000 MAD |
| micromagma_ma | 7,000 | MAD | Smartphones, Tablets, Chargers, Earbuds, Cables… | 30 – 18,000 MAD |

Sample product names:
- *"The Lost Stars"*, *"Hidden Journey"*, *"A Brief Shadow"* (books)
- *"Organic Apples"*, *"Fresh Salmon"*, *"Premium Coffee"* (grocery)
- *"Samsung Smartphone Pro 2024"*, *"Nike Running Shoes"* (Jumia)
- *"Processeur Core i7 12th Gen"*, *"RTX 4070 24Go"*, *"Samsung SSD 1To NVMe"* (UltraPC)
- *"iPhone 15 Pro"*, *"Anker Power Bank 20000mAh"*, *"JBL AirPods Pro"* (Micromagma)

---

## Kafka Integration

Kafka is used as the **real-time message bus** between scrapers and storage.

**Data flow:**
```
Scrapy spider
    │ KafkaPipeline (priority 275 in pipelines.py)
    ▼
Kafka topic: price.raw
    │ consumer.py
    ▼
data/kafka_stream/stream.jsonl
    │ data_loader.py (auto-picked up)
    ▼
Streamlit dashboard
```

**Run it:**
```bash
# 1. Start Kafka + Zookeeper
docker compose --profile kafka up -d

# 2. Start consumer (terminal A)
python kafka/consumer.py

# 3. Stream demo data (terminal B)
python kafka/producer.py --delay 0.01    # 100 items/s
python kafka/producer.py --source jumia_ma   # one source only

# 4. Or activate in Scrapy — add to .env:
KAFKA_PUSH_ENABLED=true
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
# Then run a spider normally:
scrapy crawl books_spider
```

The `KafkaPipeline` in `scrapers/pipelines.py` is always registered but is a no-op until `KAFKA_PUSH_ENABLED=true`. It fails gracefully if Kafka is not running.

---

## Monitoring

Prometheus scrapes metrics from:
- `api_service:8000/metrics` — HTTP request rate, latency (p50/p95), error rate
- `sink_service:8001/metrics` — ingest rate
- `airflow_statsd:8125` — DAG parse time, task instances

Grafana auto-provisions:
- Prometheus datasource at `http://prometheus:9090`
- Pre-built dashboard with 7 panels (request rate, latency, error rates, Airflow metrics, ingest rate)

```bash
docker compose --profile monitoring up -d
# Grafana: http://localhost:3000  (admin/admin)
# Prometheus: http://localhost:9090
```

---

## Data Quality

`analytics/validate_data.py` runs 18 checks:

| Check | Threshold |
|---|---|
| Required columns present | All 6 must exist |
| Null rate per column | < 1% |
| Price > 0 | 100% |
| Price < 1,000,000 | 100% |
| IQR outlier rate | < 5% |
| Known source names only | 100% |
| Timestamp sanity | > 2020-01-01 |
| No future timestamps | 100% |
| Title completeness | ≥ 3 chars |
| Rating in [0, 5] | 100% |

```bash
python analytics/validate_data.py --fail-on-error --json-report
# Output: analytics/reports/ge_validation.json
```

---

## Quick Start

### Prerequisites
- Ubuntu 22.04+ / WSL2 / macOS
- Docker ≥ 24 + Docker Compose v2
- Python 3.11+

### 1. Clone & install
```bash
git clone https://github.com/RADAHassan/Real-Time-E-commerce-Price-Intelligence-Platform.git
cd Real-Time-E-commerce-Price-Intelligence-Platform
cp .env.example .env          # edit as needed
pip3 install -r requirements.txt --break-system-packages --user
```

### 2. Launch the dashboard (no Docker needed)
```bash
python3 -m streamlit run dashboard/app.py --server.port=8501
# → http://localhost:8501
# 67,000 products load automatically from data/demo/demo_products.jsonl
```

### 3. Generate fresh demo data
```bash
python3 scripts/generate_demo_data.py
# Creates data/demo/demo_products.jsonl  (~14.5 MB, 66,000 rows)
```

### 4. Run scrapers (real data)
```bash
scrapy crawl books_spider -s MAX_PAGES=5
scrapy crawl jumia_spider
# Output: data/<spider_name>/<spider_name>_<timestamp>.jsonl
# Dashboard picks it up automatically on next refresh
```

### 5. Start infrastructure services
```bash
docker compose --profile bigtable up -d    # Bigtable emulator
docker compose --profile kafka up -d       # Kafka + Zookeeper
docker compose --profile nifi up -d        # Apache NiFi
docker compose --profile airflow up -d     # Airflow webserver + scheduler
docker compose --profile monitoring up -d  # Prometheus + Grafana
docker compose --profile fullstack up -d   # FastAPI + React
```

### 6. Run analytics notebooks
```bash
jupyter notebook analytics/notebooks/
# 01_descriptive_stats.ipynb
# 02_inferential_stats.ipynb
```

### 7. Run dbt transformations
```bash
cd dbt_project
dbt run
dbt test
dbt docs generate && dbt docs serve
```

### 8. Data quality check
```bash
python analytics/validate_data.py --fail-on-error --json-report
```

---

## Development Phases

| Phase | Description | Status |
|---|---|---|
| **0** | Bootstrap — repo structure, Docker Compose skeleton, Makefiles | ✅ Done |
| **1** | Scrapy spiders — 5 sites, ValidationPipeline, JsonOutputPipeline | ✅ Done |
| **2** | Bigtable emulator + schema + BigtableClient + BigtablePipeline | ✅ Done |
| **3** | NiFi streaming flow + HTTP sink microservice + KafkaPipeline | ✅ Done |
| **4** | Airflow DAGs (daily scrape + dbt + weekly report) | ✅ Done |
| **5** | dbt models + tests + macros (staging → intermediate → 4 marts) | ✅ Done |
| **6** | Statistical notebooks (descriptive + inferential, SciPy/statsmodels) | ✅ Done |
| **7** | Streamlit dashboard (4 pages) + FastAPI + React frontend | ✅ Done |
| **8** | CI/CD (GitHub Actions) + DataOps + data quality validation | ✅ Done |
| **9** | Terraform GCP provisioning (Bigtable, BigQuery, Cloud Run) | ✅ Done |
| **10** | 67K demo dataset + Kafka producer/consumer + final README | ✅ Done |

---

## Make Commands

```bash
make help            # List all commands

# Core
make install         # Install Python dependencies
make env             # Copy .env.example → .env
make up              # Start Bigtable emulator
make down            # Stop all containers

# Scrapers
make scrape-books          # Crawl books.toscrape.com
make scrape-books-sample   # 2-page fast sample
make scrape-scrapeme       # Crawl scrapeme.live
make scrape-all            # All spiders

# Dashboard
make dashboard       # Start Streamlit on :8501

# Kafka
make up-kafka        # Start Kafka + Zookeeper
# Then: python kafka/producer.py --delay 0.01
# Then: python kafka/consumer.py

# Airflow
make airflow-up      # Start Airflow (webserver + scheduler + init)
make airflow-trigger-scrape   # Trigger daily_full_scrape DAG
make airflow-trigger-dbt      # Trigger dbt_transformations DAG

# dbt
make dbt-run         # Run all dbt models
make dbt-test        # Run dbt schema + custom tests
make dbt-docs        # Generate + serve docs at :8080

# Tests & Quality
make test            # pytest
make test-cov        # pytest + coverage report
make lint            # ruff check
make format          # black formatter
make check           # lint + format check (no writes)

# Monitoring
make up-monitoring   # Prometheus :9090 + Grafana :3000

# Cleanup
make clean           # Remove __pycache__, .pyc, temp files
make clean-all       # Full reset (removes venv + Docker volumes)
```

---

## CI/CD

GitHub Actions runs on every push to `main`:

1. **Lint** — `ruff check` + `black --check`
2. **Test** — `pytest tests/` with coverage
3. **Docker build check** — builds all 5 Dockerfiles to catch errors early

Workflow file: `.github/workflows/ci.yml`

---

## Author

**Hassan RADA** · Final Year Data Engineering Project · 2025-2026

GitHub: [RADAHassan](https://github.com/RADAHassan)

---

## License

MIT
