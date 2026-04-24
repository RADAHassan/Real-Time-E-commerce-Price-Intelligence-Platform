# =============================================================================
# Real-Time E-commerce Price Intelligence Platform — Makefile
# Usage: make <target>
# =============================================================================

SHELL := /bin/bash
PYTHON := python3
VENV := .venv
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff
BLACK := $(VENV)/bin/black

.DEFAULT_GOAL := help

# =============================================================================
# Help
# =============================================================================
.PHONY: help
help: ## Show this help message
	@echo ""
	@echo "  Real-Time E-commerce Price Intelligence Platform"
	@echo "  ================================================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}'
	@echo ""

# =============================================================================
# Python environment
# =============================================================================
.PHONY: install
install: ## Create venv and install all dependencies
	@echo "→ Creating virtual environment..."
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "✓ Virtual environment ready. Activate with: source $(VENV)/bin/activate"

.PHONY: install-dev
install-dev: install ## Install dev dependencies (lint, test, notebook)
	$(PIP) install -r requirements-dev.txt

.PHONY: venv
venv: ## Create virtual environment only (no packages)
	$(PYTHON) -m venv $(VENV)

# =============================================================================
# Code quality
# =============================================================================
.PHONY: lint
lint: ## Run ruff linter on all Python files
	$(RUFF) check .

.PHONY: lint-fix
lint-fix: ## Run ruff with auto-fix
	$(RUFF) check --fix .

.PHONY: format
format: ## Format code with black
	$(BLACK) .

.PHONY: format-check
format-check: ## Check formatting without modifying files
	$(BLACK) --check .

.PHONY: check
check: lint format-check ## Run all code quality checks

# =============================================================================
# Tests
# =============================================================================
.PHONY: test
test: ## Run all tests with pytest
	$(PYTEST) tests/ -v --tb=short

.PHONY: test-cov
test-cov: ## Run tests with coverage report
	$(PYTEST) tests/ -v --cov=. --cov-report=term-missing --cov-report=html

.PHONY: test-scrapers
test-scrapers: ## Run scraper unit tests (no network — pure HTML fixtures)
	$(PYTEST) tests/scrapers/ -v

.PHONY: test-fast
test-fast: ## Run tests excluding slow integration tests
	$(PYTEST) tests/ -v -m "not slow"

# =============================================================================
# Docker Compose
# =============================================================================
.PHONY: up
up: ## Start all core services (bigtable emulator)
	docker compose --profile bigtable up -d
	@echo "✓ Core services started"

.PHONY: up-nifi
up-nifi: ## Start NiFi service
	docker compose --profile nifi up -d
	@echo "✓ NiFi started at http://localhost:8080"

.PHONY: up-airflow
up-airflow: ## Start Airflow services
	docker compose --profile airflow up -d
	@echo "✓ Airflow started at http://localhost:8081"

.PHONY: up-kafka
up-kafka: ## Start Kafka + Zookeeper
	docker compose --profile kafka up -d

.PHONY: up-monitoring
up-monitoring: ## Start Prometheus + Grafana
	docker compose --profile monitoring up -d
	@echo "✓ Grafana at http://localhost:3000 | Prometheus at http://localhost:9090"

.PHONY: up-all
up-all: ## Start ALL services (heavy — needs 16GB+ RAM)
	docker compose --profile bigtable --profile nifi --profile airflow --profile monitoring up -d

.PHONY: down
down: ## Stop and remove all containers
	docker compose --profile bigtable --profile nifi --profile airflow --profile kafka --profile monitoring --profile dashboard down
	@echo "✓ All containers stopped"

.PHONY: down-v
down-v: ## Stop containers AND delete volumes (destructive!)
	docker compose --profile bigtable --profile nifi --profile airflow --profile kafka --profile monitoring --profile dashboard down -v
	@echo "✓ Containers and volumes removed"

.PHONY: logs
logs: ## Follow logs for all running services
	docker compose logs -f

.PHONY: ps
ps: ## Show running containers status
	docker compose ps

.PHONY: restart
restart: down up ## Restart core services

# =============================================================================
# Scrapers  (run from repo root — scrapy.cfg is at root)
# =============================================================================
.PHONY: scrape-books
scrape-books: ## Crawl books.toscrape.com → data/books_spider/
	$(VENV)/bin/scrapy crawl books_spider

.PHONY: scrape-scrapeme
scrape-scrapeme: ## Crawl scrapeme.live/shop → data/scrapeme_spider/
	$(VENV)/bin/scrapy crawl scrapeme_spider

.PHONY: scrape-jumia
scrape-jumia: ## Crawl jumia.ma (ordinateurs + smartphones) → data/jumia_spider/
	$(VENV)/bin/scrapy crawl jumia_spider

.PHONY: scrape-ultrapc
scrape-ultrapc: ## Crawl ultrapc.ma (laptops + PC) → data/ultrapc_spider/
	$(VENV)/bin/scrapy crawl ultrapc_spider

.PHONY: scrape-jumia-sample
scrape-jumia-sample: ## Crawl jumia.ma — 1 page par catégorie (test rapide)
	$(VENV)/bin/scrapy crawl jumia_spider -s MAX_PAGES=1 -s HTTPCACHE_ENABLED=true

.PHONY: scrape-ultrapc-sample
scrape-ultrapc-sample: ## Crawl ultrapc.ma — 1 page par catégorie (test rapide)
	$(VENV)/bin/scrapy crawl ultrapc_spider -s MAX_PAGES=1 -s HTTPCACHE_ENABLED=true

.PHONY: scrape-micromagma
scrape-micromagma: ## Crawl micromagma.ma → data/micromagma_spider/
	$(VENV)/bin/scrapy crawl micromagma_spider

.PHONY: scrape-micromagma-sample
scrape-micromagma-sample: ## Crawl micromagma.ma — 1 page par catégorie (test rapide)
	$(VENV)/bin/scrapy crawl micromagma_spider -s MAX_PAGES=1 -s HTTPCACHE_ENABLED=true

.PHONY: scrape-all
scrape-all: scrape-books scrape-scrapeme scrape-jumia scrape-ultrapc scrape-micromagma ## Run all spiders sequentially

.PHONY: scrape-books-sample
scrape-books-sample: ## Crawl books.toscrape.com — 2 pages only (quick test)
	$(VENV)/bin/scrapy crawl books_spider -s MAX_PAGES=2 -s HTTPCACHE_ENABLED=true

# =============================================================================
# NiFi + Sink (Phase 3)
# =============================================================================
.PHONY: nifi-up
nifi-up: ## Start NiFi + Bigtable Sink containers
	docker compose --profile bigtable --profile nifi up -d
	@echo "✓ Bigtable emulator + NiFi + Sink started"
	@echo "  NiFi UI  → http://localhost:8080/nifi  (admin / adminpassword123)"
	@echo "  Sink     → http://localhost:8087/health"
	@echo "  Wait ~90s for NiFi to fully start, then run: make nifi-wait"

.PHONY: nifi-wait
nifi-wait: ## Block until NiFi is ready to accept API calls
	$(VENV)/bin/python nifi/scripts/wait_for_nifi.py --url http://localhost:8080 --timeout 180

.PHONY: nifi-deploy
nifi-deploy: ## Create the price intelligence flow in NiFi via REST API
	$(VENV)/bin/python nifi/scripts/deploy.py \
		--nifi-url http://localhost:8080 \
		--sink-url http://sink:8087/ingest \
		--listen-port 9191 \
		--start
	@echo "✓ Flow deployed — template saved to nifi/templates/"

.PHONY: nifi-deploy-local
nifi-deploy-local: ## Deploy flow pointing to localhost sink (no Docker network)
	$(VENV)/bin/python nifi/scripts/deploy.py \
		--nifi-url http://localhost:8080 \
		--sink-url http://localhost:8087/ingest \
		--listen-port 9191 \
		--start

.PHONY: nifi-dry-run
nifi-dry-run: ## Preview deploy actions without touching NiFi
	$(VENV)/bin/python nifi/scripts/deploy.py --dry-run

.PHONY: sink-up
sink-up: ## Run the Bigtable sink locally (without Docker)
	BIGTABLE_EMULATOR_HOST=localhost:8086 $(VENV)/bin/uvicorn sink.app:app \
		--host 0.0.0.0 --port 8087 --reload

.PHONY: sink-test-write
sink-test-write: ## Send a test item to the running sink
	$(VENV)/bin/python -c "\
import requests, json, hashlib, datetime; \
url='https://www.jumia.ma/hp-test.html'; \
r=requests.post('http://localhost:8087/ingest', json={ \
  'product_id': hashlib.md5(url.encode()).hexdigest(), \
  'source': 'jumia.ma', 'url': url, 'title': 'HP Test [Phase3]', \
  'price': 4299.0, 'currency': 'MAD', 'pipeline': 'manual-test', \
  'scraped_at': datetime.datetime.utcnow().isoformat()}); \
print(r.status_code, r.json())"

# =============================================================================
# Bigtable (Phase 2)
# =============================================================================
.PHONY: bigtable-up
bigtable-up: ## Start the Bigtable emulator container
	docker compose --profile bigtable up -d
	@echo "✓ Bigtable emulator starting on localhost:8086 — wait ~10s then run make bigtable-init"

.PHONY: bigtable-init
bigtable-init: ## Create the 'prices' table + column families on the emulator
	BIGTABLE_EMULATOR_HOST=localhost:8086 $(VENV)/bin/python -m bigtable.cli init-schema

.PHONY: bigtable-test-write
bigtable-test-write: ## Write a test record to verify the connection
	BIGTABLE_EMULATOR_HOST=localhost:8086 $(VENV)/bin/python -m bigtable.cli write-test

.PHONY: bigtable-scan
bigtable-scan: ## Scan and display all rows in the 'prices' table
	BIGTABLE_EMULATOR_HOST=localhost:8086 $(VENV)/bin/python -m bigtable.cli scan-all --limit 50

.PHONY: bigtable-reset
bigtable-reset: ## Drop and recreate the 'prices' table (dev reset)
	BIGTABLE_EMULATOR_HOST=localhost:8086 $(VENV)/bin/python -m bigtable.cli drop-schema
	BIGTABLE_EMULATOR_HOST=localhost:8086 $(VENV)/bin/python -m bigtable.cli init-schema

# =============================================================================
# Airflow (Phase 4)
# =============================================================================
.PHONY: airflow-build
airflow-build: ## Build the custom Airflow image (includes project deps)
	docker compose --profile airflow build

.PHONY: airflow-up
airflow-up: ## Start Airflow (webserver + scheduler + postgres + bigtable emulator)
	docker compose --profile bigtable --profile airflow up -d
	@echo "✓ Airflow UI → http://localhost:8081  (admin / admin)"

.PHONY: airflow-init
airflow-init: ## Initialise the Airflow DB and create admin user
	docker compose --profile airflow run --rm airflow-init

.PHONY: airflow-trigger-scrape
airflow-trigger-scrape: ## Manually trigger daily_full_scrape DAG run
	docker compose --profile airflow exec airflow-webserver \
		airflow dags trigger daily_full_scrape

.PHONY: airflow-trigger-dbt
airflow-trigger-dbt: ## Manually trigger dbt_transformations DAG run
	docker compose --profile airflow exec airflow-webserver \
		airflow dags trigger dbt_transformations

.PHONY: airflow-trigger-report
airflow-trigger-report: ## Manually trigger weekly_stats_report DAG run
	docker compose --profile airflow exec airflow-webserver \
		airflow dags trigger weekly_stats_report

.PHONY: airflow-list-dags
airflow-list-dags: ## List all DAGs registered in Airflow
	docker compose --profile airflow exec airflow-webserver airflow dags list

.PHONY: test-airflow
test-airflow: ## Run DAG integrity tests (skipped if airflow not installed)
	$(PYTEST) tests/airflow/ -v

# =============================================================================
# dbt
# =============================================================================
.PHONY: dbt-deps
dbt-deps: ## Install dbt packages
	cd dbt_project && ../$(VENV)/bin/dbt deps

.PHONY: dbt-compile
dbt-compile: ## Compile dbt project (no DB connection needed)
	cd dbt_project && ../$(VENV)/bin/dbt compile

.PHONY: dbt-run
dbt-run: ## Run dbt models
	cd dbt_project && ../$(VENV)/bin/dbt run

.PHONY: dbt-test
dbt-test: ## Run dbt tests
	cd dbt_project && ../$(VENV)/bin/dbt test

.PHONY: dbt-docs
dbt-docs: ## Generate and serve dbt docs
	cd dbt_project && ../$(VENV)/bin/dbt docs generate
	cd dbt_project && ../$(VENV)/bin/dbt docs serve --port 8082

# =============================================================================
# FastAPI + React fullstack (Phase 7)
# =============================================================================
.PHONY: api-up
api-up: ## Run FastAPI API locally (mock data, no GCP needed)
	USE_MOCK_DATA=true $(VENV)/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

.PHONY: api-up-bq
api-up-bq: ## Run FastAPI API against real BigQuery
	USE_MOCK_DATA=false $(VENV)/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

.PHONY: frontend-install
frontend-install: ## Install Node dependencies for the React frontend
	cd frontend && npm ci

.PHONY: frontend-dev
frontend-dev: ## Start Vite dev server (proxies /api to localhost:8000)
	cd frontend && npm run dev

.PHONY: frontend-build
frontend-build: ## Build the React app for production
	cd frontend && npm run build

.PHONY: up-fullstack
up-fullstack: ## Start API + React frontend + Bigtable via Docker Compose
	docker compose --profile bigtable --profile fullstack up -d
	@echo "✓ Frontend → http://localhost:3000"
	@echo "  API      → http://localhost:8000"

.PHONY: test-api
test-api: ## Run FastAPI endpoint tests
	USE_MOCK_DATA=true $(PYTEST) tests/api/ -v

# =============================================================================
# Terraform (Phase 9)
# =============================================================================
.PHONY: tf-init
tf-init: ## Initialise Terraform working directory
	cd infra/terraform && terraform init

.PHONY: tf-plan
tf-plan: ## Show Terraform execution plan
	cd infra/terraform && terraform plan -var="project_id=$(GCP_PROJECT_ID)"

.PHONY: tf-apply
tf-apply: ## Apply Terraform changes (creates GCP resources)
	cd infra/terraform && terraform apply -var="project_id=$(GCP_PROJECT_ID)" -auto-approve

.PHONY: tf-destroy
tf-destroy: ## Destroy all GCP resources managed by Terraform
	cd infra/terraform && terraform destroy -var="project_id=$(GCP_PROJECT_ID)"

# =============================================================================
# Dashboard
# =============================================================================
.PHONY: dashboard
dashboard: ## Start Streamlit dashboard locally
	$(VENV)/bin/streamlit run dashboard/app.py --server.port=8501

# =============================================================================
# Utilities
# =============================================================================
.PHONY: env
env: ## Copy .env.example to .env if not exists
	@if [ ! -f .env ]; then cp .env.example .env && echo "✓ .env created from .env.example — fill in your values"; \
	else echo "⚠ .env already exists, skipping"; fi

.PHONY: clean
clean: ## Remove Python cache files, logs, temp files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.log" -delete 2>/dev/null || true
	find . -name ".coverage" -delete 2>/dev/null || true
	@echo "✓ Cache and temp files removed"

.PHONY: clean-all
clean-all: clean down-v ## Full clean: cache + docker volumes
	rm -rf $(VENV)
	@echo "✓ Full clean done (venv removed)"

.PHONY: demo
demo: ## Run the full end-to-end demo (Phase 10)
	@echo "→ Starting demo..."
	@$(MAKE) up
	@sleep 5
	@$(MAKE) scrape-books
	@echo "✓ Demo complete — open http://localhost:8501"

.PHONY: setup-git
setup-git: ## Initialize git and add remote
	git init
	git remote add origin https://github.com/RADAHassan/Real-Time-E-commerce-Price-Intelligence-Platform.git
	@echo "✓ Git initialized with remote"
