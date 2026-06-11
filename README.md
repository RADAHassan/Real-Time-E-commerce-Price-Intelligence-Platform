# Real-Time E-commerce Price Intelligence Platform

> End-to-end hybrid batch + streaming data engineering platform for e-commerce price monitoring.
> Final-year academic project — Group 4 · 2025-2026

---

## Team

| # | Name | Role | Owns |
|---|---|---|---|
| 1 | **Hassan RADAH** | Data Engineering, DataOps & CI/CD | Scrapy, Kafka, NiFi, Airflow, Bigtable, Docker, Terraform, GitHub Actions |
| 2 | **Khaoula BELAJAL** | Data Analytics & Transformation | dbt models, Jupyter notebooks, statistical analysis |
| 3 | **ABDOU HABOU MAHAMED** | DevOps | Kubernetes, Prometheus/Grafana |
| 4 | **Mohamed KANTOS** | Full Stack Development | FastAPI, Streamlit dashboard, React frontend, Plotly |

> For a full breakdown of responsibilities, demo scripts, and handoff points see [`docs/PRESENTATION_GUIDE.md`](docs/PRESENTATION_GUIDE.md).

---

## What This Project Does

This platform continuously scrapes product prices from 6 e-commerce websites, processes them through a multi-layer data pipeline, stores them in a time-series database, transforms them with dbt, runs statistical analysis, and displays everything in a live interactive dashboard and React SPA — built by a 4-person team with each layer owned end-to-end by one specialist.

**Live demo:**
```bash
# Analyst dashboard
python3 -m streamlit run dashboard/app.py     # → http://localhost:8501

# REST API + React SPA
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload  # → http://localhost:8000/docs
npm run dev --prefix frontend                              # → http://localhost:5173
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES (6 sites)                       │
│  books.toscrape.com · scrapeme.live · jumia.ma · ultrapc.ma        │
│  micromagma.ma · cdiscount.com                                      │
└──────────────────────────┬──────────────────────────────────────────┘
                           │  Scrapy spiders (5-stage item pipeline)
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     INGESTION LAYER                                 │
│                                                                     │
│  ┌─────────────────┐    ┌──────────────────┐    ┌───────────────┐  │
│  │  Apache Kafka   │    │   Apache NiFi    │    │  JSONL files  │  │
│  │  (streaming)    │    │  (HTTP routing)  │    │  (archive)    │  │
│  └────────┬────────┘    └────────┬─────────┘    └───────┬───────┘  │
│           └─────────────────────┴──────────────────────┘           │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      STORAGE LAYER                                  │
│                                                                     │
│  Google Cloud Bigtable  (time-series, row_key: source#id#ts)       │
│  ClickHouse             (columnar analytical store)                 │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │  Apache Airflow (batch scheduler)
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   TRANSFORMATION LAYER — dbt + BigQuery             │
│                                                                     │
│   staging/      raw → cleaned, typed, deduped                      │
│   intermediate/ dedup (ROW_NUMBER) + price change (LAG)            │
│   marts/        mart_price_stats · mart_price_history               │
│                 mart_price_alerts · mart_current_prices             │
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
│        ANOVA, Kruskal-Wallis, Mann-Whitney, OLS regression, CI     │
│                                                                     │
│   analytics/validate_data.py  (18 data quality checks)             │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  PRESENTATION LAYER                                 │
│                                                                     │
│   FastAPI  REST API  (:8000)    — BigQuery / JSONL read path       │
│   Streamlit dashboard (:8501)   — Internal analyst tool (4 pages)  │
│   React SPA  (:5173)            — External stakeholder interface    │
└─────────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────────────────────────────────────────┐
│                  OBSERVABILITY                                      │
│   Prometheus (:9090) · Grafana (:3000) — pre-built dashboard       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Version | Owner |
|---|---|---|---|
| Scraping | Scrapy + BeautifulSoup | 2.x | Member 1 — Hassan RADAH |
| Streaming | Apache Kafka | 7.6 (Confluent) | Member 1 — Hassan RADAH |
| HTTP Routing | Apache NiFi | 1.25 | Member 1 — Hassan RADAH |
| Orchestration | Apache Airflow | 2.9 | Member 1 — Hassan RADAH |
| Storage | Google Cloud Bigtable (emulator) | SDK 2.x | Member 1 — Hassan RADAH |
| Analytical Store | ClickHouse | 24.3 | Member 1 — Hassan RADAH |
| Data Quality | Custom validation (18 checks) | — | Member 1 — Hassan RADAH |
| SQL Transforms | dbt-bigquery | 1.7 | Member 2 — Khaoula BELAJAL |
| Analytics | Python · SciPy · statsmodels · Pandas | — | Member 2 — Khaoula BELAJAL |
| Containerisation | Docker Compose · Dockerfiles (5 images) | — | Member 1 — Hassan RADAH |
| Infrastructure as Code | Terraform (GCP) | — | Member 1 — Hassan RADAH |
| CI/CD | GitHub Actions (ci / cd / security) | — | Member 1 — Hassan RADAH |
| Container Orchestration | Kubernetes · kustomize | — | Member 3 — ABDOU HABOU MAHAMED |
| Monitoring | Prometheus 2.51 · Grafana 10.4 | — | Member 3 — ABDOU HABOU MAHAMED |
| API | FastAPI | 0.111 | Member 4 — Mohamed KANTOS |
| Dashboard | Streamlit · Plotly | — | Member 4 — Mohamed KANTOS |
| Frontend | React 18 + TypeScript + Vite + Recharts | 18 | Member 4 — Mohamed KANTOS |

---

## Project Structure

```
price-intelligence-platform/
│
├── scrapers/                  Scrapy project
│   ├── spiders/               6 spiders (one per site)
│   ├── pipelines.py           Validation → JSONL → Bigtable → Kafka → NiFi
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
│   └── export_to_bigquery.py  Bigtable → BigQuery export
│
├── clickhouse/
│   ├── client.py              ClickHouse query client
│   └── schema.sql             Table definitions
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
│   └── validate_data.py       18-check data quality CLI
│
├── api/                       FastAPI read-path (BigQuery / JSONL)
│   ├── main.py                9 endpoints + Swagger UI at /docs
│   └── analysis.py            SciPy statistical analysis endpoints
│
├── dashboard/
│   ├── app.py                 Streamlit dashboard (~1,600 lines, 4 pages)
│   └── data_loader.py         Bigtable → BigQuery → JSONL priority chain
│
├── frontend/                  React 18 + TypeScript + Vite + Recharts
│   └── src/
│       ├── pages/             LivePrices, StatisticalAnalysis, PriceAlerts
│       └── api/client.ts      Typed API client
│
├── k8s/                       Kubernetes manifests (kubectl apply -k k8s/)
├── infra/terraform/           GCP: Bigtable + BigQuery + Cloud Run
├── docker/                    Dockerfiles + Prometheus/Grafana config
├── .github/workflows/         CI: lint + test + Docker build + security
└── docs/
    ├── architecture.md        Full system architecture + Mermaid diagrams
    └── PRESENTATION_GUIDE.md  Per-member demo scripts + handoff points
```

---

## The 67,000 Demo Products

| Source | Count | Currency | Categories | Price range |
|---|---|---|---|---|
| books.toscrape.com | 20,000 | GBP | 48 genres (Mystery, Sci-Fi, Romance…) | £1 – £60 |
| scrapeme.live | 11,000 | GBP | Grocery (Fruits, Dairy, Bakery, Beverages…) | £0.49 – £50 |
| jumia.ma | 20,000 | MAD | Smartphones, Fashion, Appliances, Sports… | 30 – 25,000 MAD |
| ultrapc.ma | 8,000 | MAD | CPUs, GPUs, RAM, SSDs, Monitors… | 80 – 30,000 MAD |
| micromagma.ma | 7,000 | MAD | Smartphones, Tablets, Accessories… | 30 – 18,000 MAD |
| cdiscount.com | 1,120 | EUR | Electronics, Home, Sports (France) | €5 – €2,000 |

---

## Dashboard Pages (Streamlit — localhost:8501)

### Page 1 — Live Prices
- Loads all 67,000 products in ~0.7 seconds
- Source pill filters, price range slider, availability filter, full-text search, sort chips
- KPI strip: Products, Sources, Avg price, Lowest, Highest
- Violin chart (log scale), donut chart, volume progress bars, paginated data table

### Page 2 — Historical KPIs
- Per-source KPI cards (avg, median, σ) from `mart_price_stats`
- Grouped bar chart (Min / Avg / Median / Max per source)
- Interactive trend explorer — select any product, view price over time, highlight drops ≥5%

### Page 3 — Statistical Analysis
Three tabs:
- **Descriptive** — summary stats table, distribution histogram, CV% bar chart, box plots
- **Hypothesis Tests** — Shapiro-Wilk normality; one-way ANOVA (F, η²); Kruskal-Wallis (H, ε²); pairwise Mann-Whitney U with effect size r; p-value heatmap; 95% CI forest plot
- **Regression** — OLS price ~ rating scatter with trendline; slope β₁, R², p-value; per-source regression table

### Page 4 — Price Alerts
- Severity threshold slider (−5% to −50%)
- Alert cards: yellow = mild (5–10%), orange = moderate (10–20%), red = severe (≥20%)
- Top-20 price drops horizontal bar chart + severity donut chart

---

## React Frontend (localhost:5173)

The React SPA consumes the FastAPI at `/api` (proxied through Vite in dev, Nginx in production):

- **Live Prices** — market share donut, price ranges bar chart, source intelligence table, product table with source filter chips
- **Statistical Analysis** — box plots (log10 stacked bars trick), price histogram, hypothesis test results, OLS regression scatter
- **Price Alerts** — color-coded alert cards, filter by severity

---

## Quick Start

### Prerequisites
- Ubuntu 22.04+ / WSL2 / macOS
- Docker ≥ 24 + Docker Compose v2
- Python 3.11+ · Node 18+

### 1. Clone & install
```bash
git clone https://github.com/RADAHassan/Real-Time-E-commerce-Price-Intelligence-Platform.git
cd Real-Time-E-commerce-Price-Intelligence-Platform
cp .env.example .env
pip3 install -r requirements.txt --break-system-packages --user
```

### 2. Launch the Streamlit dashboard (no Docker needed)
```bash
python3 -m streamlit run dashboard/app.py --server.port=8501
# → http://localhost:8501  (67,000 products load automatically)
```

### 3. Launch the FastAPI + React stack
```bash
# Terminal A — API
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
# → http://localhost:8000/docs

# Terminal B — React frontend
cd frontend && npm install && npm run dev
# → http://localhost:5173
```

### 4. Run scrapers (real data)
```bash
scrapy crawl books_spider -s MAX_PAGES=5
scrapy crawl jumia_spider
# Output: data/<spider_name>/<spider_name>_<timestamp>.jsonl
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
```

### 7. Run dbt transformations
```bash
cd dbt_project && dbt run && dbt test
dbt docs generate && dbt docs serve    # → http://localhost:8080
```

### 8. Data quality check
```bash
python analytics/validate_data.py --fail-on-error --json-report
```

---

## Development Phases

| Phase | Description | Status | Owner |
|---|---|---|---|
| **0** | Bootstrap — repo structure, Docker Compose skeleton, Makefiles | ✅ Done | Member 1 |
| **1** | Scrapy spiders — 6 sites, ValidationPipeline, JsonOutputPipeline | ✅ Done | Member 1 |
| **2** | Bigtable emulator + schema + BigtableClient + BigtablePipeline | ✅ Done | Member 1 |
| **3** | NiFi streaming flow + HTTP sink microservice + KafkaPipeline | ✅ Done | Member 1 |
| **4** | Airflow DAGs (daily scrape + dbt + weekly report) | ✅ Done | Member 1 |
| **5** | dbt models + tests + macros (staging → intermediate → 4 marts) | ✅ Done | Member 2 |
| **6** | Statistical notebooks (descriptive + inferential, SciPy/statsmodels) | ✅ Done | Member 2 |
| **7** | Streamlit dashboard (4 pages) + FastAPI + React SPA | ✅ Done | Member 4 |
| **8** | CI/CD (GitHub Actions) + Docker images + Terraform + DataOps | ✅ Done | Member 1 |
| **9** | Kubernetes manifests + Prometheus/Grafana monitoring | ✅ Done | Member 3 |
| **10** | 67K demo dataset + Kafka producer/consumer + final documentation | ✅ Done | All |

---

## CI/CD

GitHub Actions runs on every push to `main`:

| Job | What it does |
|---|---|
| `python` | `ruff` lint → `black` format check → `pytest` with coverage → `dbt compile` |
| `frontend` | `npm ci` → TypeScript check → production build |
| `docker` | Builds all 5 images (api, sink, frontend, dashboard, airflow) with layer cache |
| `scrapers` | `scrapy list` + 2-page cached crawl to validate spider output |

**Security** (`.github/workflows/security.yml`): pip-audit, npm audit, Trivy container scan (SARIF → GitHub Security tab), gitleaks secret detection — runs weekly.

---

## Team

| Role | Name |
|---|---|
| Data Engineering & DataOps | **Hassan RADAH** |
| Data Analytics & Transformation | **Khaoula BELAJAL** |
| DevOps | **ABDOU HABOU MAHAMED** |
| Full Stack Development | **Mohamed KANTOS** |

Final Year Academic Project · 2025-2026

---

## License

MIT
