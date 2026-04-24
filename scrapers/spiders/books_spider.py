"""
BooksSpider — crawls books.toscrape.com, a sandboxed practice site.
Follows pagination automatically and visits each book's detail page to get
full metadata (category from breadcrumb, clean availability text, image URL).

Row key strategy (preview for Bigtable Phase 2):
  product_id = MD5(canonical_url)  →  unique per book edition
"""

import hashlib
import logging
from datetime import datetime, timezone

import scrapy

from scrapers.items import PriceItem

logger = logging.getLogger(__name__)

# books.toscrape.com encodes star ratings as CSS class names
_RATING_MAP = {
    "One": 1.0,
    "Two": 2.0,
    "Three": 3.0,
    "Four": 4.0,
    "Five": 5.0,
}


class BooksSpider(scrapy.Spider):
    name = "books_spider"
    allowed_domains = ["books.toscrape.com"]
    start_urls = ["https://books.toscrape.com/catalogue/page-1.html"]

    # Limit pages during development; override via -s MAX_PAGES=0 (0 = unlimited)
    custom_settings = {
        "MAX_PAGES": 0,
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

        for book in response.css("article.product_pod"):
            detail_href = book.css("h3 a::attr(href)").get()
            if detail_href:
                yield response.follow(detail_href, callback=self.parse_book)

        if self.max_pages and self._pages_crawled >= self.max_pages:
            logger.info("Reached MAX_PAGES=%d — stopping pagination", self.max_pages)
            return

        next_href = response.css("li.next a::attr(href)").get()
        if next_href:
            yield response.follow(next_href, callback=self.parse)

    # ------------------------------------------------------------------
    # Detail page
    # ------------------------------------------------------------------

    def parse_book(self, response):
        title = response.css("div.product_main h1::text").get("").strip()

        # Price comes as "£51.77" or "Â£51.77" (encoding artifact on some pages)
        raw_price = response.css("p.price_color::text").get("0").strip()
        price = _parse_price(raw_price)

        # Star rating encoded as: <p class="star-rating Three">
        rating_class = response.css("p.star-rating::attr(class)").get("")
        rating_word = rating_class.split()[-1] if rating_class else ""
        rating = _RATING_MAP.get(rating_word)

        # Availability: grab all text nodes and join
        avail_parts = response.css("p.availability::text").getall()
        availability = " ".join(p.strip() for p in avail_parts if p.strip())

        # Category: 3rd breadcrumb item (Home > Books > <Category>)
        crumbs = response.css("ul.breadcrumb li a::text").getall()
        category = crumbs[2].strip() if len(crumbs) > 2 else ""

        # Image URL
        raw_img = response.css("div#product_gallery img::attr(src)").get(
            response.css("div.item.active img::attr(src)").get("")
        )
        image_url = response.urljoin(raw_img) if raw_img else ""

        product_id = hashlib.md5(response.url.encode()).hexdigest()

        yield PriceItem(
            product_id=product_id,
            source="books.toscrape.com",
            url=response.url,
            title=title,
            price=price,
            currency="GBP",
            rating=rating,
            availability=availability,
            category=category,
            image_url=image_url,
            scraped_at=datetime.now(timezone.utc).isoformat(),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_price(raw: str) -> float:
    """Strip currency symbols and unicode artifacts, return float."""
    cleaned = raw.encode("ascii", errors="ignore").decode()
    for char in ("£", "$", "€", ",", " "):
        cleaned = cleaned.replace(char, "")
    try:
        return float(cleaned)
    except ValueError:
        logger.warning("Could not parse price: %r", raw)
        return 0.0
