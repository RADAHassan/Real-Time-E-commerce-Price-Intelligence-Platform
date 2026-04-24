"""
ScrapemeSpider — crawls scrapeme.live/shop/, a WooCommerce demo site built
explicitly for scraping practice (see https://scrapeme.live).
Products are Pokémon-themed items with GBP prices — a second "market" to
compare against books.toscrape.com in the analytics phase.

Row key strategy (preview for Bigtable Phase 2):
  product_id = MD5(canonical_url)  →  unique per product page
"""

import hashlib
import logging
from datetime import datetime, timezone

import scrapy

from scrapers.items import PriceItem

logger = logging.getLogger(__name__)


class ScrapemeSpider(scrapy.Spider):
    name = "scrapeme_spider"
    allowed_domains = ["scrapeme.live"]
    start_urls = ["https://scrapeme.live/shop/page/1/"]

    custom_settings = {
        # scrapeme.live is a low-traffic demo site — be extra polite
        "DOWNLOAD_DELAY": 3,
    }

    def __init__(self, *args, max_pages: int = 0, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_pages = int(max_pages)
        self._pages_crawled = 0

    # ------------------------------------------------------------------
    # Listing page
    # ------------------------------------------------------------------

    def parse(self, response):
        self._pages_crawled += 1

        for product in response.css("li.product"):
            detail_href = product.css("a.woocommerce-loop-product__link::attr(href)").get()
            if detail_href:
                yield response.follow(detail_href, callback=self.parse_product)

        if self.max_pages and self._pages_crawled >= self.max_pages:
            logger.info("Reached MAX_PAGES=%d — stopping pagination", self.max_pages)
            return

        next_href = response.css("a.next.page-numbers::attr(href)").get()
        if next_href:
            yield response.follow(next_href, callback=self.parse)

    # ------------------------------------------------------------------
    # Detail page
    # ------------------------------------------------------------------

    def parse_product(self, response):
        title = response.css("h1.product_title::text").get("").strip()

        # WooCommerce price: <span class="woocommerce-Price-amount amount"><bdi>£63.00</bdi></span>
        raw_price = response.css(
            "p.price span.woocommerce-Price-amount bdi::text"
        ).get("") or response.css("p.price ins span.woocommerce-Price-amount bdi::text").get("")
        price = _parse_price(raw_price.strip())

        # Stock status
        stock_text = response.css("p.stock::text").get("").strip()
        availability = "In Stock" if "in stock" in stock_text.lower() else "Out of Stock"

        # Category from WooCommerce breadcrumb or category widget
        # <span class="posted_in"><a>Pokémon</a></span>
        category = response.css("span.posted_in a::text").get("").strip()

        # Rating (WooCommerce uses aria-label on the stars element)
        rating_label = response.css("div.woocommerce-product-rating .star-rating::attr(aria-label)").get("")
        rating = _parse_wc_rating(rating_label)

        image_url = response.css("div.woocommerce-product-gallery__image a::attr(href)").get(
            response.css("div.woocommerce-product-gallery img::attr(src)").get("")
        )

        product_id = hashlib.md5(response.url.encode()).hexdigest()

        yield PriceItem(
            product_id=product_id,
            source="scrapeme.live",
            url=response.url,
            title=title,
            price=price,
            currency="GBP",
            rating=rating,
            availability=availability,
            category=category,
            image_url=image_url or "",
            scraped_at=datetime.now(timezone.utc).isoformat(),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_price(raw: str) -> float:
    cleaned = raw.encode("ascii", errors="ignore").decode()
    for char in ("£", "$", "€", ",", " "):
        cleaned = cleaned.replace(char, "")
    try:
        return float(cleaned)
    except ValueError:
        logger.warning("Could not parse price: %r", raw)
        return 0.0


def _parse_wc_rating(aria_label: str) -> float | None:
    """Parse '3.00 out of 5' style aria-label → float."""
    if not aria_label:
        return None
    try:
        return float(aria_label.split()[0])
    except (ValueError, IndexError):
        return None
