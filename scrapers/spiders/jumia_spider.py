"""
JumiaSpider — crawls product listings on jumia.ma.

Cibles par défaut : ordinateurs portables + smartphones.
Les pages de listing Jumia contiennent déjà titre, prix, rating et image —
on n'a pas besoin de visiter les pages détail, ce qui réduit la charge réseau.

Currency : MAD (Dirham marocain), format français "4 299,00 DH".
Rating  : encodé via CSS width (ex. "width:80%" = 4 étoiles sur 5).

robots.txt : respecté via ROBOTSTXT_OBEY = True dans settings.py.
Rate limiting : DOWNLOAD_DELAY = 3s + AutoThrottle + 1 req/domain.

⚠  Si Jumia retourne des pages vides ou 403, activer SCRAPY_HTTPCACHE=true
   pour inspecter la réponse brute et ajuster les headers si nécessaire.
"""

import hashlib
import logging
from datetime import datetime, timezone

import scrapy

from scrapers.items import PriceItem
from scrapers.utils import _parse_mad_price, _parse_star_width

logger = logging.getLogger(__name__)

# Catégories cibles — ajouter/retirer selon les besoins du projet
_START_CATEGORIES = [
    "ordinateurs-portables",
    "smartphones",
    "tablettes",
    "televisions",
]


class JumiaSpider(scrapy.Spider):
    name = "jumia_spider"
    allowed_domains = ["jumia.ma"]
    start_urls = [f"https://www.jumia.ma/{cat}/" for cat in _START_CATEGORIES]

    custom_settings = {
        # Extra prudent sur un vrai site commercial
        "DOWNLOAD_DELAY": 3,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        # Headers courants pour réduire le risque de blocage
        "DEFAULT_REQUEST_HEADERS": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-MA,fr;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
        },
    }

    def __init__(self, *args, max_pages: int = 0, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_pages = int(max_pages)
        # Compteur par catégorie (URL de base) pour respecter max_pages
        self._pages: dict[str, int] = {}

    # ------------------------------------------------------------------
    # Listing page
    # ------------------------------------------------------------------

    def parse(self, response):
        # Clé de catégorie = dernier segment de l'URL de départ
        cat_key = response.url.rstrip("/").split("/")[-1].split("?")[0]
        self._pages[cat_key] = self._pages.get(cat_key, 0) + 1

        products = response.css("article.prd")
        if not products:
            logger.warning(
                "[jumia] Aucun produit trouvé sur %s — "
                "vérifier les sélecteurs ou activer SCRAPY_HTTPCACHE=true pour inspecter.",
                response.url,
            )

        for article in products:
            title = article.css("h3.name::text").get("").strip()
            raw_price = article.css("div.prc::text").get("").strip()
            price = _parse_mad_price(raw_price)

            href = article.css("a.core::attr(href)").get("")
            product_url = response.urljoin(href)

            # Rating : largeur CSS en % → étoiles sur 5
            star_style = article.css("div.stars > div::attr(style)").get("")
            rating = _parse_star_width(star_style)

            # Image : Jumia utilise data-src pour le lazy-load
            img = (
                article.css("img.img::attr(data-src)").get()
                or article.css("img.img::attr(src)").get("")
            )

            # Disponibilité : badge "Rupture de stock" si absent du panier
            out_of_stock = bool(article.css("div.s-info").get())
            availability = "Out of Stock" if out_of_stock else "In Stock"

            # Catégorie lisible depuis le fil d'Ariane ou l'URL
            category = cat_key.replace("-", " ").title()

            if not title or price == 0.0:
                logger.debug("[jumia] Article ignoré (titre ou prix manquant) : %s", product_url)
                continue

            product_id = hashlib.md5(product_url.encode()).hexdigest()

            yield PriceItem(
                product_id=product_id,
                source="jumia.ma",
                url=product_url,
                title=title,
                price=price,
                currency="MAD",
                rating=rating,
                availability=availability,
                category=category,
                image_url=img,
                scraped_at=datetime.now(timezone.utc).isoformat(),
            )

        if self.max_pages and self._pages.get(cat_key, 0) >= self.max_pages:
            logger.info("[jumia] MAX_PAGES=%d atteint pour '%s'", self.max_pages, cat_key)
            return

        # Pagination Jumia — deux sélecteurs possibles selon la version du site
        next_href = response.css(
            "a[aria-label='Next Page']::attr(href), "
            "a.pg.-ar::attr(href)"
        ).get()
        if next_href:
            yield response.follow(next_href, callback=self.parse)
