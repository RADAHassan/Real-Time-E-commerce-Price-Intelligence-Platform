"""
Unit tests for UltraPCSpider.
Fake HTML reproduit la structure PrestaShop de ultrapc.ma — aucun appel réseau.
"""

import pytest
from scrapy.http import Request

from scrapers.items import PriceItem
from scrapers.spiders.ultrapc_spider import UltraPCSpider
from tests.scrapers.conftest import fake_response


# ---------------------------------------------------------------------------
# Fixtures HTML
# ---------------------------------------------------------------------------


@pytest.fixture
def ultrapc_listing_html():
    """Page catégorie laptops — structure PrestaShop article.product-miniature."""
    return """
    <html><body>
      <nav class="breadcrumb">
        <ol>
          <li><span>Accueil</span></li>
          <li><span>Laptops</span></li>
        </ol>
      </nav>
      <section id="products">
        <article class="product-miniature">
          <h2 class="product-title">
            <a href="https://www.ultrapc.ma/laptops/asus-vivobook-15.html">
              ASUS VivoBook 15 i5-1235U 8Go 512Go SSD
            </a>
          </h2>
          <span class="price">8 999,00 MAD</span>
          <img class="img-fluid"
               src="https://www.ultrapc.ma/img/asus-vivobook.jpg"
               alt="ASUS VivoBook">
        </article>
        <article class="product-miniature">
          <h2 class="product-title">
            <a href="https://www.ultrapc.ma/laptops/lenovo-ideapad-5.html">
              Lenovo IdeaPad 5 i7-1255U 16Go 1To SSD
            </a>
          </h2>
          <span class="price">13 500,00 MAD</span>
          <img class="img-fluid"
               src="https://www.ultrapc.ma/img/lenovo-ideapad.jpg"
               alt="Lenovo">
          <span class="product-unavailable">Rupture de stock</span>
        </article>
        <article class="product-miniature">
          <h2 class="product-title">
            <a href="https://www.ultrapc.ma/laptops/produit-sans-prix.html">
              Produit sans prix
            </a>
          </h2>
          <span class="price"></span>
        </article>
      </section>
      <a rel="next" href="https://www.ultrapc.ma/19-laptops?page=2">Suivant</a>
    </body></html>
    """


@pytest.fixture
def ultrapc_detail_html():
    """Page détail produit PrestaShop — prix actualisé + catégorie + stock."""
    return """
    <html><body>
      <nav class="breadcrumb">
        <ol>
          <li><span>Accueil</span></li>
          <li><span>Laptops</span></li>
          <li><span>ASUS VivoBook 15 i5-1235U</span></li>
        </ol>
      </nav>
      <div class="product-prices">
        <span class="price">8 799,00 MAD</span>
      </div>
      <img class="js-qv-product-cover"
           src="https://www.ultrapc.ma/img/hi-res-asus.jpg" alt="ASUS">
    </body></html>
    """


@pytest.fixture
def ultrapc_detail_out_of_stock_html():
    return """
    <html><body>
      <nav class="breadcrumb">
        <ol>
          <li><span>Accueil</span></li>
          <li><span>Composants</span></li>
          <li><span>Carte Mère MSI</span></li>
        </ol>
      </nav>
      <div class="product-prices">
        <span class="price">2 200,00 MAD</span>
      </div>
      <span class="label-out-of-stock">Rupture de stock</span>
    </body></html>
    """


# ---------------------------------------------------------------------------
# Tests listing page
# ---------------------------------------------------------------------------


def test_listing_yields_requests_for_detail(ultrapc_listing_html):
    spider = UltraPCSpider()
    response = fake_response("https://www.ultrapc.ma/19-laptops", ultrapc_listing_html)

    results = list(spider.parse(response))
    # Les pages détail ont ".html" dans l'URL — la pagination n'en a pas
    detail_reqs = [r for r in results if isinstance(r, Request) and r.url.endswith(".html")]
    # 3 articles mais 1 sans prix → 2 requêtes vers pages détail
    assert len(detail_reqs) == 2


def test_listing_skips_zero_price(ultrapc_listing_html):
    spider = UltraPCSpider()
    response = fake_response("https://www.ultrapc.ma/19-laptops", ultrapc_listing_html)

    results = list(spider.parse(response))
    detail_reqs = [r for r in results if isinstance(r, Request) and "sans-prix" in r.url]
    assert len(detail_reqs) == 0


def test_listing_follows_next_page(ultrapc_listing_html):
    spider = UltraPCSpider()
    response = fake_response("https://www.ultrapc.ma/19-laptops", ultrapc_listing_html)

    results = list(spider.parse(response))
    next_reqs = [r for r in results if isinstance(r, Request) and "page=2" in r.url]
    assert len(next_reqs) == 1


def test_listing_stops_at_max_pages(ultrapc_listing_html):
    spider = UltraPCSpider(max_pages=1)
    response = fake_response("https://www.ultrapc.ma/19-laptops", ultrapc_listing_html)

    results = list(spider.parse(response))
    next_reqs = [r for r in results if isinstance(r, Request) and "page=2" in r.url]
    assert len(next_reqs) == 0


# ---------------------------------------------------------------------------
# Tests detail page
# ---------------------------------------------------------------------------


def test_detail_yields_item_with_updated_price(ultrapc_detail_html):
    spider = UltraPCSpider()
    url = "https://www.ultrapc.ma/laptops/asus-vivobook-15.html"

    # Simuler un partial_item issu du listing
    partial = PriceItem(
        product_id="abc",
        source="ultrapc.ma",
        url=url,
        title="ASUS VivoBook 15 i5-1235U 8Go 512Go SSD",
        price=8999.0,        # prix listing
        currency="MAD",
        rating=None,
        availability="In Stock",
        category="Laptops",
        image_url="https://www.ultrapc.ma/img/asus-vivobook.jpg",
        scraped_at="2026-04-24T12:00:00+00:00",
    )

    response = fake_response(url, ultrapc_detail_html)
    items = list(spider._parse_detail(response, partial))

    assert len(items) == 1
    item = items[0]
    # Prix mis à jour depuis la page détail
    assert item["price"] == pytest.approx(8799.0)
    # Image haute résolution récupérée
    assert "hi-res" in item["image_url"]
    # Catégorie depuis fil d'Ariane (avant-dernier)
    assert item["category"] == "Laptops"
    assert item["availability"] == "In Stock"


def test_detail_out_of_stock(ultrapc_detail_out_of_stock_html):
    spider = UltraPCSpider()
    url = "https://www.ultrapc.ma/composants/carte-mere-msi.html"

    partial = PriceItem(
        product_id="def",
        source="ultrapc.ma",
        url=url,
        title="Carte Mère MSI B450",
        price=2500.0,
        currency="MAD",
        rating=None,
        availability="In Stock",
        category="Composants",
        image_url="",
        scraped_at="2026-04-24T12:00:00+00:00",
    )

    response = fake_response(url, ultrapc_detail_out_of_stock_html)
    items = list(spider._parse_detail(response, partial))

    assert items[0]["availability"] == "Out of Stock"
    assert items[0]["price"] == pytest.approx(2200.0)
    assert items[0]["category"] == "Composants"


def test_detail_product_id_preserved(ultrapc_detail_html):
    spider = UltraPCSpider()
    url = "https://www.ultrapc.ma/laptops/asus-vivobook-15.html"
    partial = PriceItem(
        product_id="original-id-must-not-change",
        source="ultrapc.ma",
        url=url,
        title="ASUS",
        price=1.0,
        currency="MAD",
        scraped_at="2026-04-24T12:00:00+00:00",
    )
    response = fake_response(url, ultrapc_detail_html)
    item = next(spider._parse_detail(response, partial))
    assert item["product_id"] == "original-id-must-not-change"
