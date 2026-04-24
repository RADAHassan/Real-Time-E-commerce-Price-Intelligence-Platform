"""
Scrapy project settings — controls rate limiting, middlewares, pipelines, and output.
All tuneable values are driven by environment variables so no secrets live in code.
"""

import os
from dotenv import load_dotenv

load_dotenv()

BOT_NAME = "price_intelligence"
SPIDER_MODULES = ["scrapers.spiders"]
NEWSPIDER_MODULE = "scrapers.spiders"

# Respect robots.txt — non-negotiable
ROBOTSTXT_OBEY = True

# ---------------------------------------------------------------------------
# Rate limiting — be a polite scraper
# ---------------------------------------------------------------------------
DOWNLOAD_DELAY = float(os.getenv("SCRAPY_DOWNLOAD_DELAY", "2"))
RANDOMIZE_DOWNLOAD_DELAY = True          # actual delay = 0.5x–1.5x DOWNLOAD_DELAY

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0
AUTOTHROTTLE_MAX_DELAY = 15.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0   # target 1 request in-flight per domain
AUTOTHROTTLE_DEBUG = False

CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 2

# ---------------------------------------------------------------------------
# Retry — handle transient errors gracefully
# ---------------------------------------------------------------------------
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# ---------------------------------------------------------------------------
# Downloader middlewares
# ---------------------------------------------------------------------------
DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": 90,
    "scrapers.middlewares.RotateUserAgentMiddleware": 400,
    "scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware": 810,
}

# ---------------------------------------------------------------------------
# Item pipelines (order matters: lower number runs first)
# ---------------------------------------------------------------------------
ITEM_PIPELINES = {
    "scrapers.pipelines.ValidationPipeline": 100,
    "scrapers.pipelines.JsonOutputPipeline": 200,
    "scrapers.pipelines.NiFiHttpPipeline": 300,
}

# ---------------------------------------------------------------------------
# HTTP cache — useful during development to avoid hammering sites
# ---------------------------------------------------------------------------
HTTPCACHE_ENABLED = os.getenv("SCRAPY_HTTPCACHE", "false").lower() == "true"
HTTPCACHE_EXPIRATION_SECS = 3600
HTTPCACHE_DIR = ".scrapy/httpcache"
HTTPCACHE_POLICY = "scrapy.extensions.httpcache.DummyPolicy"

# ---------------------------------------------------------------------------
# NiFi integration (activated in Phase 3)
# ---------------------------------------------------------------------------
NIFI_INGEST_URL = os.getenv("NIFI_INGEST_URL", "")
NIFI_PUSH_ENABLED = os.getenv("NIFI_PUSH_ENABLED", "false").lower() == "true"

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
FEED_EXPORT_ENCODING = "utf-8"
LOG_LEVEL = os.getenv("SCRAPY_LOG_LEVEL", "INFO")

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
