# Real-Time E-commerce Price Intelligence Platform

> End-to-end hybrid batch + streaming platform for e-commerce price monitoring.
> Final-year data engineering project.

---

## Architecture Overview

```
Web Scraping (Scrapy)
        │
        ├──────────────────────────────────────────────┐
        ▼                                              ▼
[Streaming] Apache NiFi                  [Batch] Apache Airflow
        │                                              │
        └──────────────────┬───────────────────────────┘
                           ▼
             Google Cloud Bigtable
             (time-series storage)
                           │
                           ▼
             dbt + BigQuery external tables
             (staging → intermediate → marts)
                           │
                           ▼
           Python Analytics (SciPy, statsmodels)
           Descriptive + Inferential statistics
                           │
                           ▼
         Streamlit Dashboard + Real-time Alerts
```

Full Mermaid diagram: [docs/architecture.md](docs/architecture.md)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Scraping | Scrapy 2.x, BeautifulSoup, Selenium |
| Streaming | Apache NiFi 1.25 |
| Batch Orchestration | Apache Airflow 2.9 |
| Storage | Google Cloud Bigtable (emulator locally) |
| SQL Transformations | dbt-bigquery |
| Analytics | Python, Pandas, SciPy, statsmodels, pingouin |
| Visualisation | Plotly, Streamlit |
| Infrastructure | Docker Compose, Kubernetes, Terraform |
| CI/CD | GitHub Actions |
| Data Quality | Great Expectations |
| Monitoring | Prometheus + Grafana |
| Python tooling | pip + venv, ruff, black, pytest |

---

## Project Structure

```
price-intelligence-platform/
├── scrapers/                  # Scrapy project
│   ├── spiders/               #   Individual spiders per site
│   ├── pipelines.py           #   Output: JSON + HTTP push to NiFi
│   └── settings.py
├── nifi/
│   ├── templates/             # NiFi flow templates (XML)
│   └── scripts/               # REST API deployment scripts
├── airflow/
│   ├── dags/                  # Airflow DAGs
│   └── plugins/               # Custom operators
├── dbt_project/
│   ├── models/
│   │   ├── staging/           # Raw → cleaned
│   │   ├── intermediate/      # Joins + enrichment
│   │   └── marts/             # KPIs for dashboard
│   ├── tests/                 # Custom dbt tests
│   └── macros/
├── analytics/
│   ├── notebooks/             # Jupyter: descriptive + inferential stats
│   └── reports/               # Auto-generated HTML/PDF
├── dashboard/                 # Streamlit app
├── infra/terraform/           # GCP provisioning
├── docker/                    # Custom Dockerfiles
├── .github/workflows/         # CI + CD pipelines
├── docs/                      # Architecture diagrams
└── tests/                     # Python unit + integration tests
```

---

## Quick Start

### Prerequisites

- Ubuntu 22.04+ (or WSL2)
- Docker >= 24 + Docker Compose v2
- Python 3.11+
- `make`

### 1. Clone & configure

```bash
git clone https://github.com/RADAHassan/Real-Time-E-commerce-Price-Intelligence-Platform.git
cd Real-Time-E-commerce-Price-Intelligence-Platform
make env          # creates .env from .env.example
# Edit .env with your values
```

### 2. Install Python dependencies

```bash
make install      # creates .venv + installs requirements.txt
source .venv/bin/activate
```

### 3. Start core services (Bigtable emulator)

```bash
make up           # starts bigtable-emulator
make ps           # check status
```

### 4. Start individual service groups

```bash
make up-nifi      # NiFi at http://localhost:8080
make up-airflow   # Airflow at http://localhost:8081
make up-kafka     # Kafka on port 9092
make up-monitoring  # Grafana:3000, Prometheus:9090
```

### 5. Run tests

```bash
make test         # all unit tests
make test-cov     # with coverage report
```

### 6. Code quality

```bash
make check        # lint + format check
make lint-fix     # auto-fix lint issues
```

---

## Development Phases

| Phase | Description | Status |
|---|---|---|
| **0** | Bootstrap — repo structure, Docker skeleton | ✅ |
| **1** | Scrapy spiders (books.toscrape.com + scrapeme.live + jumia.ma + ultrapc.ma + micromagma.ma) | ✅ |
| **2** | Bigtable emulator + schema design + CLI | ✅ |
| **3** | NiFi streaming flow + Bigtable sink service | ✅ |
| **4** | Airflow DAGs (scrape + dbt + reports) | ⬜ |
| **5** | dbt models + tests + docs | ⬜ |
| **6** | Statistical analytics notebooks | ⬜ |
| **7** | Streamlit dashboard (4 pages) | ⬜ |
| **8** | DataOps: CI/CD, Great Expectations, monitoring | ⬜ |
| **9** | GCP deployment via Terraform | ⬜ |
| **10** | Final deliverables + demo video | ⬜ |

---

## Make Commands

```bash
make help          # List all available commands

# Environment
make install       # Create venv + install deps
make env           # Create .env from .env.example

# Docker
make up            # Start core services
make up-all        # Start all services (needs 16GB RAM)
make down          # Stop all containers
make logs          # Follow container logs

# Tests & Quality
make test          # Run pytest
make test-cov      # Run pytest + coverage
make lint          # Ruff linter
make format        # Black formatter
make check         # lint + format-check

# dbt
make dbt-run       # Run dbt models
make dbt-test      # Run dbt tests
make dbt-docs      # Generate + serve docs

# Scrapers
make scrape-books          # Crawl books.toscrape.com
make scrape-scrapeme       # Crawl scrapeme.live/shop
make scrape-books-sample   # 2-page sample (fast, uses HTTP cache)
make scrape-all            # Run all spiders

# Dashboard
make dashboard     # Start Streamlit locally

# Cleanup
make clean         # Remove cache files
make clean-all     # Full reset (removes venv + volumes)
```

---

## Contributing

This is a final-year academic project. Issues and suggestions are welcome via
[GitHub Issues](https://github.com/RADAHassan/Real-Time-E-commerce-Price-Intelligence-Platform/issues).

---

## License

MIT
