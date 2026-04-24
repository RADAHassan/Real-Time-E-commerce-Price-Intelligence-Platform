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
