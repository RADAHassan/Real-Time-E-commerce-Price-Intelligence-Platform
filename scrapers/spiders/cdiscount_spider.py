"""
CdiscountSpider — crawls product listings on cdiscount.com.

Cdiscount is France's second-largest e-commerce marketplace. Pages are
server-side rendered so Scrapy works without a JS engine.

Default categories: informatique, high-tech, TV, electromenager, telephonie.
Currency: EUR (French decimal format "1 299,99 €").

robots.txt : respecté via ROBOTSTXT_OBEY = True dans settings.py.
Rate limiting : DOWNLOAD_DELAY = 3s + AutoThrottle + 1 req/domain.

Usage:
    scrapy crawl cdiscount_spider                     # all categories, all pages
    scrapy crawl cdiscount_spider -a max_pages=3      # 3 pages per category
    scrapy crawl cdiscount_spider -a category=tv-son  # single category

Note on selectors:
    Cdiscount updates its CSS class names periodically. If yields drop to zero,
    run: scrapy shell "https://www.cdiscount.com/informatique/r-informatique.html"
    and inspect with response.css('...') to find the current product card selector.
"""

import hashlib
import logging
from datetime import datetime, timezone

import scrapy

from scrapers.items import PriceItem
from scrapers.utils import _parse_eur_price, _parse_star_width

logger = logging.getLogger(__name__)

# (slug, human-readable label) — added to the item's category field
_CATEGORIES = [
    ("informatique",         "Informatique"),
    ("high-tech",            "High-Tech"),
    ("tv-son",               "TV & Son"),
    ("electromenager",       "Électroménager"),
    ("telephonie",           "Téléphonie"),
]

_BASE_URL = "https://www.cdiscount.com"


def _listing_url(category_slug: str, page: int = 1) -> str:
    slug_clean = category_slug.replace("-", "_")
    base = f"{_BASE_URL}/{category_slug}/r-{slug_clean}.html"
    if page > 1:
        base += f"?CurrentPage={page}"
    return base


class CdiscountSpider(scrapy.Spider):
    name = "cdiscount_spider"
    allowed_domains = ["cdiscount.com"]

    custom_settings = {
        "DOWNLOAD_DELAY": 3,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "DEFAULT_REQUEST_HEADERS": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
        },
    }

    def __init__(self, *args, max_pages: int = 0, category: str = "", **kwargs):
        super().__init__(*args, **kwargs)
        self.max_pages = int(max_pages)
        # Allow targeting a single category via -a category=tv-son
        if category:
            self._targets = [(category, category.replace("-", " ").title())]
        else:
            self._targets = _CATEGORIES
        self._pages: dict[str, int] = {}  # slug → pages crawled so far

    def start_requests(self):
        for slug, _ in self._targets:
            yield scrapy.Request(
                _listing_url(slug, 1),
                callback=self.parse,
                meta={"cat_slug": slug},
            )

    # ------------------------------------------------------------------
    # Listing page
    # ------------------------------------------------------------------

    def parse(self, response):
        slug = response.meta["cat_slug"]
        self._pages[slug] = self._pages.get(slug, 0) + 1
        cat_label = next((lb for s, lb in self._targets if s == slug), slug)

        # Product cards — Cdiscount uses several layouts; try in order
        cards = (
            response.css("div.prdtBItm")
            or response.css("li.prdtLine")
            or response.css("article[data-productid]")
        )

        if not cards:
            logger.warning(
                "[cdiscount] No product cards on %s — selectors may need updating.",
                response.url,
            )

        for card in cards:
            # Title
            title = (
                card.css("a.prdtBITitl::text").get()
                or card.css("p.prdtBITitlInner::text").get()
                or card.css("[class*='Titl']::text").get()
                or ""
            ).strip()

            # Price — multiple selector fallbacks
            raw_price = (
                card.css("span.price::text").get()
                or card.css("div.prcxEvo span.price::text").get()
                or card.css("[class*='Price'] span::text").get()
                or card.css("[class*='price']::text").get()
                or ""
            ).strip()
            price = _parse_eur_price(raw_price)

            # Product URL
            href = (
                card.css("a.prdtBITitl::attr(href)").get()
                or card.css("a.prdtBItm::attr(href)").get()
                or card.css("a[href*='/f-']::attr(href)").get()
                or ""
            )
            product_url = response.urljoin(href) if href else response.url

            # Rating — Cdiscount stores it as a text note "4,2/5" or star div
            raw_rating = (
                card.css("span.starNote::text").get()
                or card.css("div.cmmBlocNote span::text").get()
                or card.css("[class*='starNote']::text").get()
                or ""
            ).strip()
            rating = _parse_cdiscount_rating(raw_rating)

            # Image
            img = (
                card.css("img.prdtHdImg::attr(src)").get()
                or card.css("img[class*='prdtImg']::attr(src)").get()
                or card.css("img::attr(data-src)").get()
                or card.css("img::attr(src)").get()
                or ""
            )

            # Availability
            promo_block = card.css("div.prdtBIProm").get() or ""
            availability = "Out of Stock" if "rupture" in promo_block.lower() else "In Stock"

            if not title or price <= 0:
                logger.debug(
                    "[cdiscount] Skipped card (missing title or price) on %s", response.url
                )
                continue

            product_id = hashlib.md5(product_url.encode()).hexdigest()

            yield PriceItem(
                product_id=product_id,
                source="cdiscount.com",
                url=product_url,
                title=title,
                price=price,
                currency="EUR",
                rating=rating,
                availability=availability,
                category=cat_label,
                image_url=img,
                scraped_at=datetime.now(timezone.utc).isoformat(),
            )

        # Pagination
        if self.max_pages and self._pages.get(slug, 0) >= self.max_pages:
            logger.info("[cdiscount] max_pages=%d reached for '%s'", self.max_pages, slug)
            return

        next_page = self._pages[slug] + 1
        next_url = _listing_url(slug, next_page)

        # Cdiscount listing pages return HTTP 200 even on empty pages;
        # stop following when we got zero cards on the current page
        if cards:
            yield response.follow(
                next_url,
                callback=self.parse,
                meta={"cat_slug": slug},
            )


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _parse_cdiscount_rating(raw: str) -> float | None:
    """Parse Cdiscount note formats:
      "4,2/5"  → 4.2
      "4.2"    → 4.2
      "(123)"  → None  (review count, not a rating)
    """
    import re  # noqa: PLC0415
    if not raw or raw.startswith("("):
        return None
    m = re.search(r"(\d+)[,.](\d+)", raw)
    if m:
        try:
            return float(f"{m.group(1)}.{m.group(2)}")
        except ValueError:
            pass
    m2 = re.search(r"(\d+)", raw)
    if m2:
        v = float(m2.group(1))
        return v if v <= 5 else None
    return None
