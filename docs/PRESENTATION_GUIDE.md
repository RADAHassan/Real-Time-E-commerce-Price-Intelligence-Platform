# Presentation Guide — Real-Time E-commerce Price Intelligence Platform

> This document is the internal script for the 4-person academic demo.
> It assigns talking points, demo actions, and handoff cues to each member.
> Suggested total time: **20–25 minutes** (5–6 min per member + 3 min Q&A).

---

## Presentation Order

```
[Member 1] Data Engineering, DataOps & CI/CD
        │
        │  HANDOFF A — "The raw data is in storage. Here is how it gets there."
        ▼
[Member 2] Data Analytics & Transformation
        │
        │  HANDOFF B — "The clean mart tables are in BigQuery. Docker images are built. Time to deploy."
        ▼
[Member 3] DevOps
        │
        │  HANDOFF C — "Services are deployed on Kubernetes and observable in Grafana."
        ▼
[Member 4] Full Stack Development
        │
        │  END — "The end-user sees this data here."
        ▼
[All]   Q&A
```

---

## Member 1 — Data Engineering & DataOps
**Name:** Hassan RADAH
**Elevator pitch:** *"I own everything that touches the data before it is clean — collecting it, validating it, routing it, and scheduling it — and I built the entire infrastructure layer that makes it reproducible: Docker, Terraform, and the CI/CD pipeline."*

### Talking Points

**1. Web scraping with Scrapy**
- We scrape **6 e-commerce websites** — books.toscrape.com, scrapeme.live, jumia.ma (Morocco), ultrapc.ma, micromagma.ma, and cdiscount.com (France, EUR).
- I wrote one spider per site. Each spider inherits from Scrapy's `Spider` class and yields a `PriceItem` — a fixed schema with 11 fields: `product_id`, `title`, `price`, `currency`, `source`, `url`, `rating`, `availability`, `category`, `image_url`, `scraped_at`.
- Price parsing is non-trivial: Jumia and Cdiscount use French decimal format (`"4 299,00 DH"`) — I wrote `_parse_mad_price()` and `_parse_eur_price()` in `scrapers/utils.py` to handle spaces as thousands separators and commas as decimal points.
- Rate limiting is configured globally: 2-second base delay, randomised ±50%, AutoThrottle that backs off if the server slows down. `ROBOTSTXT_OBEY = True` — we never violate robots.txt.

**2. The 5-stage item pipeline**
- Every scraped item passes through 5 pipeline stages **in order** before it reaches any storage system.
- Stage 100 — `ValidationPipeline`: drops any item with a missing required field, a non-numeric price, or a negative price. This is the first quality gate.
- Stage 200 — `JsonOutputPipeline`: appends every valid item as a JSON line to `data/<spider>/<spider>_<timestamp>.jsonl`. This creates a permanent local archive.
- Stage 250 — `BigtablePipeline`: writes to Google Cloud Bigtable using the row key `{source}#{product_id}#{scraped_at}`. This time-series key design lets us efficiently scan all price history for any product.
- Stage 275 — `KafkaPipeline`: publishes to the `price.raw` Kafka topic for real-time consumers.
- Stage 300 — `NiFiHttpPipeline`: POSTs to Apache NiFi for enterprise-grade routing to the Bigtable Sink microservice.

**3. Real-time streaming with Kafka and NiFi**
- Kafka is the **message bus**. The `KafkaPipeline` publishes each validated item as JSON to the `price.raw` topic. A consumer script subscribes and writes to `data/kafka_stream/stream.jsonl` — the dashboard picks this file up live.
- NiFi is the **routing layer**. A `ListenHTTP` processor on port 9191 receives items from Scrapy, then `InvokeHTTP` forwards them to our Sink microservice (`sink/app.py`) — a FastAPI endpoint on port 8087 that writes directly to Bigtable. I deployed the entire NiFi flow programmatically via REST API using `nifi/scripts/deploy.py`.

**4. Batch orchestration with Airflow and data quality**
- Apache Airflow schedules the entire pipeline. The `daily_full_scrape` DAG runs at 02:00 UTC — it fires all 5 spiders **in parallel**, then runs a sanity check that confirms at least one row landed in Bigtable.
- The `dbt_transformations` DAG runs at 03:00 UTC — it waits for scraping to finish using an `ExternalTaskSensor`, then loads data into BigQuery via two parallel paths (JSONL files for dev, Bigtable export for production).
- `analytics/validate_data.py` runs 18 data quality checks — null rate per column, price bounds, IQR outlier rate, timestamp sanity, known source names, rating range. It outputs a JSON report and exits with a non-zero code on failure, which makes it Airflow-compatible.

**5. Docker, Terraform & GitHub Actions CI/CD**
- I defined the entire local environment in `docker-compose.yml` using **Docker Compose profiles** — `--profile bigtable`, `--profile kafka`, `--profile nifi`, `--profile airflow`, `--profile monitoring`, `--profile fullstack`. Each service has its own Dockerfile in `docker/`. The Airflow image bakes in the scrapers code (`COPY scrapers/`, `bigtable/`, `dbt_project/`) so it works in production without volume mounts.
- `infra/terraform/main.tf` provisions the entire GCP stack from zero: 8 API activations, Bigtable instance, GCS bucket with 90-day lifecycle, 3 BigQuery datasets, Artifact Registry, and a service account with minimum IAM roles. Everything is reproducible in under 5 minutes.
- `.github/workflows/ci.yml` runs on every push: lint → tests → dbt compile → React build → 5 Docker images in a matrix job with layer cache. `.github/workflows/cd.yml` pushes images to GHCR and deploys to Cloud Run. `.github/workflows/security.yml` runs weekly: `pip-audit`, `npm audit`, Trivy container scans (SARIF → GitHub Security tab), and gitleaks secret detection.

### Demo Actions
1. Open `http://localhost:8081` (Airflow) → show the `daily_full_scrape` DAG graph view.
2. Run `make scrape-books-sample` in the terminal — show items appearing in `data/books_spider/`.
3. Show `scrapers/pipelines.py` briefly — point to the 5 stage numbers (100, 200, 250, 275, 300).
4. Run `python analytics/validate_data.py` — show the 18 checks passing.
5. Show `.github/workflows/ci.yml` — point to the 4-job structure and the 5-image Docker matrix.

---

## HANDOFF A — Member 1 → Member 2

> **Member 1 says:**
> *"At this point, every product that passed validation exists in two places: as a JSONL file on disk, and as a row in Google Cloud Bigtable. The Airflow DAG has loaded all JSONL files into the `price_intelligence_raw.prices` table in BigQuery. That raw table has 67,000 rows, one per scraped observation, with no deduplication and no price-change calculations yet. That is where [Member 2] takes over."*

**What is being handed over:**
- BigQuery table: `price_intelligence_raw.prices` — raw schema, 11 columns, day-partitioned on `scraped_at`
- JSONL files under `data/` — the same data as local files
- Bigtable `prices` table — production write path

---

## Member 2 — Data Analytics & Transformation
**Name:** Khaoula BELAJAL
**Elevator pitch:** *"I own what happens to the data after it lands in BigQuery — cleaning it, modelling it into analytics-ready tables, and running the statistical analysis that turns raw prices into actionable intelligence."*

### Talking Points

**1. dbt data modelling — 3-layer architecture**
- I built the transformation pipeline using **dbt-bigquery** with a strict 3-layer architecture inside `dbt_project/models/`.
- **Staging layer** (`stg_prices` — View): Cleans the raw data without changing its grain. Trims whitespace from title and category, casts price to `FLOAT64`, uppercases currency codes, converts `scraped_at` to a proper `TIMESTAMP`, and filters out rows below a configurable `min_price` variable. This is the single source of truth for downstream models.
- **Intermediate layer** (ephemeral — no physical table): `int_prices_deduped` removes same-day duplicates using `ROW_NUMBER() OVER (PARTITION BY product_id, scraped_date ORDER BY scraped_at DESC)` — if a product was scraped 3 times in one day, only the most recent row survives. `int_price_changes` computes `price_change_pct` and `price_change_abs` by joining each row with the **previous day's** row for the same product using a LAG window function.
- **Mart layer** (materialised as Tables — the outputs the API and dashboard actually query): `mart_price_stats` (per-source averages, medians, standard deviations), `mart_price_history` (one row per product per day with price and change), `mart_current_prices` (most recent price per product), `mart_price_alerts` (products with ≥5% drop in the last N days).

**2. Descriptive statistics — Jupyter notebook**
- `analytics/notebooks/01_descriptive_stats.ipynb` uses Pandas and SciPy to characterise the price distributions.
- For each source, I compute: mean, median, mode, standard deviation, IQR (Q75–Q25), skewness (Fisher's moment), and kurtosis (excess). I then run a **Shapiro-Wilk normality test** on each source's price distribution — none of them are normally distributed (all p < 0.001), which informs the choice of non-parametric tests in the inferential notebook.
- I also plot overlaid KDE curves per source and flag IQR outliers using the 1.5×IQR rule.

**3. Inferential statistics — Jupyter notebook**
- `analytics/notebooks/02_inferential_stats.ipynb` tests whether price differences between sources are statistically significant.
- **One-way ANOVA** (parametric): H₀ = all source means are equal. Result: F-statistic and p-value. We reject H₀, confirming the sources have significantly different pricing.
- **Kruskal-Wallis** (non-parametric equivalent, more appropriate given non-normality): same conclusion with H-statistic.
- **Pairwise Mann-Whitney U**: tests every pair of sources (e.g., books_toscrape vs. jumia_ma). Reports U-statistic, two-sided p-value, and effect size r = 1 − (2U / n₁n₂).
- **OLS linear regression**: price ~ rating. Reports slope β₁, intercept β₀, R², and p-value. A low R² here is itself informative — it means star ratings are not a reliable price predictor across these markets.
- **95% confidence intervals** on the mean price per source — visualised as a forest plot.

**4. Data quality from the analytics side**
- The dbt project includes custom `schema.yml` tests: not-null constraints on `product_id`, `price`, `source`; accepted-values tests on `currency`; relationships tests between mart and staging tables.
- Running `dbt test` after every `dbt run` ensures no mart table ships data that fails schema contracts.

### Demo Actions
1. Open `dbt_project/models/` — show the 3-folder structure (staging / intermediate / marts).
2. Run `make dbt-run` — show the SQL compilation and BigQuery execution logs.
3. Open `analytics/notebooks/01_descriptive_stats.ipynb` — show the Shapiro-Wilk table and KDE plot.
4. Open `analytics/notebooks/02_inferential_stats.ipynb` — show the ANOVA result and the pairwise Mann-Whitney table.

---

## HANDOFF B — Member 2 → Member 3

> **Member 2 says:**
> *"The 4 mart tables are now materialised in BigQuery under the `price_intelligence_marts` dataset. `mart_price_stats` has one row per source. `mart_price_history` has one row per product per day. `mart_price_alerts` has every product that dropped ≥5%. These are the tables that the API and the dashboard will query directly. The Docker images and CI/CD pipeline that deliver those services are already built — [Member 3] now takes those images and deploys them to Kubernetes, and sets up the monitoring layer so we can observe them in production."*

**What is being handed over:**
- BigQuery dataset `price_intelligence_marts` with 4 tables
- The dbt `profiles.yml` connection config
- Documented table schemas (via `dbt docs generate`)

---

## Member 3 — DevOps
**Name:** ABDOU HABOU MAHAMED
**Elevator pitch:** *"I own the deployment and monitoring layer — the Kubernetes manifests that deploy every service to production, and the Prometheus/Grafana stack that monitors them once they are running."*

### Talking Points

**1. Kubernetes — production container orchestration**
- I wrote the full `k8s/` manifest set deployable with a single command: `kubectl apply -k k8s/`.
- `namespace.yaml` isolates all resources in the `price-intelligence` namespace.
- `configmap.yaml` externalises all env vars (GCP project ID, Kafka broker, dataset names) so no credentials live in code. A `Secret` object holds the GCP service account key.
- `api-deployment.yaml` and `dashboard-deployment.yaml` define rolling deployments with `livenessProbe` and `readinessProbe` health checks — the API probes `/health`, the dashboard probes Streamlit's built-in `/_stcore/health`.
- `scraper-cronjob.yaml` runs all spiders as a Kubernetes `CronJob` at `0 2 * * *`, mirroring the Airflow schedule for cloud-native deployments.
- `ingress.yaml` routes `/api` to FastAPI and `/` to the Streamlit dashboard through a single Nginx ingress controller.

**2. Prometheus & Grafana — observability**
- Prometheus scrapes metrics from all running services. Grafana visualises request rate, latency (p50/p95), error rate, Airflow DAG success rate, and Bigtable ingest throughput.
- Both services auto-provision on `docker compose --profile monitoring up` — Grafana loads its datasource and dashboard JSON from `monitoring/` at startup, so there is no manual configuration.

### Demo Actions
1. Run `make k8s-status` — show pods, services, and ingress in the `price-intelligence` namespace.
2. Open `http://localhost:3000` (Grafana) — show the pre-built dashboard with live metrics.
3. Open `http://localhost:9090` (Prometheus) — run a quick query like `http_requests_total`.

---

## HANDOFF C — Member 3 → Member 4

> **Member 3 says:**
> *"Every service is running: the FastAPI container is up on port 8000, the Streamlit dashboard container is up on port 8501, and both have been deployed to Cloud Run. The API is connected to the `price_intelligence_marts` BigQuery dataset. [Member 4] built everything the end-user actually sees and interacts with — the API, the dashboard, and the React frontend."*

**What is being handed over:**
- Running FastAPI service at `http://localhost:8000` with `/docs` (Swagger UI)
- Running Streamlit dashboard at `http://localhost:8501`
- Running React frontend at `http://localhost:3000`
- Docker images in GHCR, deployed to Cloud Run

---

## Member 4 — Full Stack Development
**Name:** Mohamed KANTOS
**Elevator pitch:** *"I own the end-user experience — the REST API that exposes the clean data, the interactive Streamlit dashboard that analysts use daily, and the React frontend that external stakeholders access."*

### Talking Points

**1. FastAPI — read-path REST API**
- `api/main.py` is a FastAPI application with a clean dual-mode design: when `USE_MOCK_DATA=true` (the default for local development), it serves hardcoded sample data from `api/mock_data.py` with no cloud credentials needed. When `USE_MOCK_DATA=false`, it queries the BigQuery mart tables via the Google Cloud Python SDK.
- Key endpoints: `GET /health` (liveness probe), `GET /products` (paginated, filterable by source/category/price), `GET /stats` (one row per source from `mart_price_stats`), `GET /history/{product_id}` (price over time from `mart_price_history`), `GET /alerts` (price drops from `mart_price_alerts`).
- CORS middleware is configured to accept requests from the React frontend's origin. The entire API is documented automatically at `/docs` (Swagger UI).

**2. Streamlit dashboard — 4-page analytics tool**
- `dashboard/app.py` is a ~1,500-line Streamlit application with a custom dark UI built entirely in CSS injected via `st.markdown(..., unsafe_allow_html=True)`. The design is inspired by tools like Linear and Vercel — dark `#07101f` background, Inter font, animated pill filter buttons, sort chips.
- The data loading chain in `dashboard/data_loader.py` has a priority fallback: Bigtable emulator → BigQuery marts → local JSONL files. In demo mode it reads the 67,000-product JSONL dataset directly, loading in under 1 second.
- **Page 1 — Live Prices**: full-width search bar, price range slider, source pill filters (colour-coded per source), availability filter, sort chips (Price ↑/↓, Rating ↓, Name A→Z), 5 KPI cards, violin chart (log scale), donut chart, animated progress bars, and a paginated data table.
- **Page 2 — Historical KPIs**: per-source KPI cards showing avg/median/σ from `mart_price_stats`, a grouped bar chart of min/avg/median/max, and an interactive product trend explorer with drop annotations.
- **Page 3 — Statistical Analysis**: three tabs — Descriptive (summary stats table, histogram, CV% chart, box plots), Hypothesis Tests (Shapiro-Wilk, ANOVA, Kruskal-Wallis, pairwise Mann-Whitney with a p-value heatmap, 95% CI forest plot), Regression (OLS scatter with trendline, R² KPI cards, per-source regression table).
- **Page 4 — Price Alerts**: reads `mart_price_alerts`, shows colour-coded alert cards (yellow = mild 5–10%, orange = moderate 10–20%, red = severe ≥20%), a severity threshold slider, and a horizontal bar chart of the top 20 price drops.

**3. React frontend — external-facing SPA**
- `frontend/` is a React 18 + TypeScript application built with Vite, served by Nginx in production.
- It consumes the FastAPI read-path API at `/api`, proxied through Nginx so there is no CORS issue in production.
- The frontend is the public-facing layer — the dashboard is the internal analyst tool, the React app is what you would show external stakeholders or embed in a company intranet.

**4. Plotly chart engineering**
- All charts in the dashboard are Plotly figures styled with a shared `CHART_BASE` layout dict — transparent backgrounds, the Inter font, a dark grid at `#1a2640`, consistent margins.
- Specific engineering decisions: violin charts filter `price > 0` before applying `log_y=True` (log of zero causes Plotly.js to silently blank the chart), donut charts use `textposition="inside"` to prevent labels being clipped by container margins, the `title=dict(text="")` pattern in `CHART_BASE` prevents Plotly.js from rendering the JavaScript `undefined` string as a chart title.

### Demo Actions
1. Open `http://localhost:8000/docs` — show the Swagger UI and run a live `GET /stats` query.
2. Open `http://localhost:8501` — walk through all 4 dashboard pages.
   - Page 1: type "samsung" in the search bar, show filtered results.
   - Page 2: select a product in the trend explorer, toggle "Highlight drops".
   - Page 3: switch to Hypothesis Tests tab — show the ANOVA and the p-value heatmap.
   - Page 4: move the severity slider to −20% — show only severe alerts.
3. Show `dashboard/app.py` lines 54–65 — explain `CHART_BASE` and why `title=dict(text="")` matters.

---

## Handoff Summary (Quick Reference)

| Handoff | From | To | What crosses the boundary |
|---|---|---|---|
| **A** | Member 1 (Ingest) | Member 2 (Transform) | Raw table `price_intelligence_raw.prices` in BigQuery, JSONL files on disk |
| **B** | Member 2 (Transform) | Member 3 (DevOps) | 4 mart tables in `price_intelligence_marts`, `dbt docs` site |
| **C** | Member 3 (DevOps) | Member 4 (Full Stack) | Running Kubernetes pods (API :8000, Dashboard :8501, Frontend :3000), Cloud Run URLs |

---

## Q&A — Likely Professor Questions

| Question | Who answers | Key point |
|---|---|---|
| "Why Bigtable and not PostgreSQL?" | Member 1 | Bigtable's row key `{source}#{product_id}#{ts}` is designed for time-series range scans — PostgreSQL would need a time-series extension and heavy indexing to match this performance at scale. |
| "Why dbt instead of writing SQL directly in Airflow?" | Member 2 | dbt gives us version-controlled, tested, documented SQL with automatic lineage. Every model has schema tests. `dbt docs generate` produces a browsable data catalog automatically. |
| "What happens if a spider is blocked?" | Member 1 | AutoThrottle backs off, the Retry middleware retries up to 3 times on 429/5xx. The ValidationPipeline drops malformed items silently. The Airflow DAG marks the task as failed and retries once after 5 minutes. |
| "How does the dashboard update in real-time?" | Member 4 | The `@st.cache_data(ttl=120)` decorator invalidates the JSONL cache every 2 minutes. With `KAFKA_PUSH_ENABLED=true`, the consumer writes to `data/kafka_stream/stream.jsonl` continuously and the dashboard picks it up on the next cache refresh. |
| "Why Kubernetes if you already have Docker Compose?" | Member 3 | Docker Compose is for local development. Kubernetes provides pod restarts on failure, rolling deployments with zero downtime, horizontal scaling via replica counts, and health-probe-driven traffic routing — none of which Compose offers. |
| "What is the statistical conclusion from the data?" | Member 2 | Prices differ significantly between sources (ANOVA p < 0.001, Kruskal-Wallis p < 0.001). Price and rating are weakly correlated (R² ≈ 0.05 to 0.15 depending on source) — star ratings are not a reliable price signal across these markets. |

---

## Suggested Time Split

| Segment | Duration | Who |
|---|---|---|
| Introduction — what the project does, architecture overview | 2 min | Any member (or rotate) |
| Member 1 — Data Engineering, DataOps & CI/CD | 6 min | Hassan RADAH |
| Member 2 — Data Analytics & Transformation | 5 min | Khaoula BELAJAL |
| Member 3 — DevOps | 4 min | ABDOU HABOU MAHAMED |
| Member 4 — Full Stack Development | 5 min | Mohamed KANTOS |
| Q&A | 3 min | All |

**Total: ~25 minutes**
