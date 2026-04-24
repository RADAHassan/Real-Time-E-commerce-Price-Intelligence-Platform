"""
MicromagmaSpider — crawls product listings on micromagma.ma.

Micromagma est un revendeur IT marocain (PrestaShop).
Stratégie identique à UltraPCSpider :
  listing (titre, prix, image) → détail (prix finalisé, catégorie, stock).

Currency : MAD — format "4 999,00 DH" ou "4 999 MAD".
robots.txt : respecté via ROBOTSTXT_OBEY = True dans settings.py.

⚠  Si les sélecteurs ne matchent pas au premier test live, activer
   SCRAPY_HTTPCACHE=true et inspecter response.css("...").getall() en shell :
   scrapy shell 'https://www.micromagma.ma/ordinateurs-portables'
"""

import hashlib
import logging
from datetime import datetime, timezone

import scrapy

from scrapers.items import PriceItem
from scrapers.utils import _parse_mad_price

logger = logging.getLogger(__name__)

_CATEGORY_URLS = [
    "https://www.micromagma.ma/ordinateurs-portables",
    "https://www.micromagma.ma/pc-de-bureau",
    "https://www.micromagma.ma/ecrans-moniteurs",
    "https://www.micromagma.ma/smartphones-tablettes",
    "https://www.micromagma.ma/composants",
    "https://www.micromagma.ma/peripheriques",
    "https://www.micromagma.ma/reseaux-et-securite",
]


class MicromagmaSpider(scrapy.Spider):
    name = "micromagma_spider"
    allowed_domains = ["micromagma.ma"]
    start_urls = _CATEGORY_URLS

    custom_settings = {
        "DOWNLOAD_DELAY": 2,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "DEFAULT_REQUEST_HEADERS": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-MA,fr;q=0.9,ar;q=0.8,en;q=0.7",
        },
    }

    def __init__(self, *args, max_pages: int = 0, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_pages = int(max_pages)
        self._pages: dict[str, int] = {}

    # ------------------------------------------------------------------
    # Listing page
    # ------------------------------------------------------------------

    def parse(self, response):
        base_url = response.url.split("?")[0].rstrip("/")
        self._pages[base_url] = self._pages.get(base_url, 0) + 1

        products = (
            response.css("article.product-miniature")
            or response.css("div.product-container")
            or response.css("li.ajax_block_product")
        )

        if not products:
            logger.warning(
                "[micromagma] Aucun produit sur %s — sélecteurs à vérifier.",
                response.url,
            )

        for product in products:
            title = (
                product.css("h2.product-title a::text").get()
                or product.css("h3.product-title a::text").get()
                or product.css("p.product-title a::text").get()
                or product.css("a.product_name::text").get("")
            ).strip()

            href = (
                product.css("h2.product-title a::attr(href)").get()
                or product.css("h3.product-title a::attr(href)").get()
                or product.css("a.product_img_link::attr(href)").get("")
            )
            product_url = response.urljoin(href)

            raw_price = (
                product.css("span.price::text").get()
                or product.css("span.product-price::text").get()
                or product.css("div.price span::text").get("")
            ).strip()
            price = _parse_mad_price(raw_price)

            img = (
                product.css("img.img-fluid::attr(src)").get()
                or product.css("img::attr(data-src)").get()
                or product.css("img::attr(src)").get("")
            )
            image_url = response.urljoin(img) if img else ""

            out_of_stock = bool(
                product.css("span.product-unavailable").get()
                or product.css(".out_of_stock").get()
            )
            availability = "Out of Stock" if out_of_stock else "In Stock"

            category = response.css(
                "nav.breadcrumb li:last-child span::text, "
                "ol.breadcrumb li:last-child::text"
            ).get("").strip() or base_url.rstrip("/").split("/")[-1].replace("-", " ").title()

            if not title or price == 0.0:
                logger.debug("[micromagma] Ignoré (titre/prix manquant) : %s", product_url)
                continue

            product_id = hashlib.md5(product_url.encode()).hexdigest()

            yield scrapy.Request(
                product_url,
                callback=self._parse_detail,
                cb_kwargs={
                    "partial_item": PriceItem(
                        product_id=product_id,
                        source="micromagma.ma",
                        url=product_url,
                        title=title,
                        price=price,
                        currency="MAD",
                        rating=None,
                        availability=availability,
                        category=category,
                        image_url=image_url,
                        scraped_at=datetime.now(timezone.utc).isoformat(),
                    )
                },
            )

        if self.max_pages and self._pages.get(base_url, 0) >= self.max_pages:
            logger.info("[micromagma] MAX_PAGES=%d atteint pour '%s'", self.max_pages, base_url)
            return

        next_href = response.css(
            "a[rel='next']::attr(href), "
            "a.next::attr(href), "
            "li.next a::attr(href)"
        ).get()
        if next_href:
            yield response.follow(next_href, callback=self.parse)

    # ------------------------------------------------------------------
    # Detail page
    # ------------------------------------------------------------------

    def _parse_detail(self, response, partial_item: PriceItem):
        raw_price = (
            response.css("span.current-price span::text").get()
            or response.css("div.product-prices span.price::text").get()
            or response.css("span#our_price_display::text").get("")
        ).strip()
        if raw_price:
            updated = _parse_mad_price(raw_price)
            if updated > 0:
                partial_item["price"] = updated

        crumbs = response.css(
            "nav.breadcrumb li span::text, "
            "ol.breadcrumb li span::text, "
            "div#nav-breadcrumb a::text"
        ).getall()
        if len(crumbs) >= 2:
            partial_item["category"] = crumbs[-2].strip()

        out = bool(
            response.css("span.label-out-of-stock").get()
            or response.css(".out_of_stock").get()
            or "rupture" in response.text.lower()
        )
        partial_item["availability"] = "Out of Stock" if out else "In Stock"

        hi_res = response.css(
            "img.js-qv-product-cover::attr(src), "
            "img#bigpic::attr(src)"
        ).get()
        if hi_res:
            partial_item["image_url"] = response.urljoin(hi_res)

        yield partial_item
