"""
Unit tests for JumiaSpider.
Fake HTML reproduit la structure réelle de jumia.ma — aucun appel réseau.
"""

import pytest
from scrapy.http import Request

from scrapers.items import PriceItem
from scrapers.spiders.jumia_spider import JumiaSpider
from tests.scrapers.conftest import fake_response


# ---------------------------------------------------------------------------
# Fixtures HTML représentatives de jumia.ma
# ---------------------------------------------------------------------------


@pytest.fixture
def jumia_listing_html():
    """Page de listing ordinateurs portables — structure article.prd."""
    return """
    <html><body>
      <main>
        <article class="prd _box col c-prd">
          <a class="core" href="/hp-pavilion-15-123456.html">
            <div class="info">
              <h3 class="name">HP Pavilion 15 Core i5 8Go 512Go SSD</h3>
              <div class="prc">4 299,00 DH</div>
              <div class="stars _s">
                <div style="width:80%"></div>
              </div>
            </div>
            <img class="img" data-src="https://img.jumia.ma/hp-pavilion.jpg" alt="HP">
          </a>
        </article>
        <article class="prd _box col c-prd">
          <a class="core" href="/dell-inspiron-15-456789.html">
            <div class="info">
              <h3 class="name">Dell Inspiron 15 Core i7 16Go 1To SSD</h3>
              <div class="prc">7 999,00 DH</div>
              <div class="stars _s">
                <div style="width:60%"></div>
              </div>
              <div class="s-info">Rupture de stock</div>
            </div>
            <img class="img" src="https://img.jumia.ma/dell-inspiron.jpg" alt="Dell">
          </a>
        </article>
        <article class="prd _box col c-prd">
          <a class="core" href="/no-price-product.html">
            <div class="info">
              <h3 class="name">Produit sans prix</h3>
              <div class="prc"></div>
            </div>
          </a>
        </article>
      </main>
      <a aria-label="Next Page" href="/ordinateurs-portables/?page=2">→</a>
    </body></html>
    """


@pytest.fixture
def jumia_listing_no_next_html():
    """Dernière page de listing — pas de lien suivant."""
    return """
    <html><body>
      <article class="prd _box col c-prd">
        <a class="core" href="/laptop-last.html">
          <div class="info">
            <h3 class="name">Dernier Laptop</h3>
            <div class="prc">3 500,00 DH</div>
          </div>
        </a>
      </article>
    </body></html>
    """


# ---------------------------------------------------------------------------
# Tests listing page
# ---------------------------------------------------------------------------


def test_listing_yields_items_and_skips_no_price(jumia_listing_html):
    spider = JumiaSpider()
    response = fake_response(
        "https://www.jumia.ma/ordinateurs-portables/", jumia_listing_html
    )
    items = [r for r in spider.parse(response) if isinstance(r, PriceItem)]
    # 3 articles dans le HTML, mais "Produit sans prix" doit être ignoré
    assert len(items) == 2


def test_listing_item_fields(jumia_listing_html):
    spider = JumiaSpider()
    response = fake_response(
        "https://www.jumia.ma/ordinateurs-portables/", jumia_listing_html
    )
    items = [r for r in spider.parse(response) if isinstance(r, PriceItem)]
    hp = items[0]

    assert hp["title"] == "HP Pavilion 15 Core i5 8Go 512Go SSD"
    assert hp["price"] == pytest.approx(4299.0)
    assert hp["currency"] == "MAD"
    assert hp["rating"] == pytest.approx(4.0)
    assert hp["source"] == "jumia.ma"
    assert hp["availability"] == "In Stock"
    assert hp["category"] == "Ordinateurs Portables"
    assert hp["image_url"] == "https://img.jumia.ma/hp-pavilion.jpg"


def test_listing_out_of_stock_detected(jumia_listing_html):
    spider = JumiaSpider()
    response = fake_response(
        "https://www.jumia.ma/ordinateurs-portables/", jumia_listing_html
    )
    items = [r for r in spider.parse(response) if isinstance(r, PriceItem)]
    dell = items[1]
    assert dell["availability"] == "Out of Stock"


def test_listing_fallback_to_src_when_no_data_src(jumia_listing_html):
    """Certains articles utilisent src au lieu de data-src pour l'image."""
    spider = JumiaSpider()
    response = fake_response(
        "https://www.jumia.ma/ordinateurs-portables/", jumia_listing_html
    )
    items = [r for r in spider.parse(response) if isinstance(r, PriceItem)]
    dell = items[1]
    assert dell["image_url"] == "https://img.jumia.ma/dell-inspiron.jpg"


def test_listing_follows_next_page(jumia_listing_html):
    spider = JumiaSpider()
    response = fake_response(
        "https://www.jumia.ma/ordinateurs-portables/", jumia_listing_html
    )
    requests = [r for r in spider.parse(response) if isinstance(r, Request)]
    assert any("page=2" in r.url for r in requests)


def test_listing_no_next_page(jumia_listing_no_next_html):
    spider = JumiaSpider()
    response = fake_response(
        "https://www.jumia.ma/ordinateurs-portables/", jumia_listing_no_next_html
    )
    requests = [r for r in spider.parse(response) if isinstance(r, Request)]
    assert len(requests) == 0


def test_listing_stops_at_max_pages(jumia_listing_html):
    spider = JumiaSpider(max_pages=1)
    response = fake_response(
        "https://www.jumia.ma/ordinateurs-portables/", jumia_listing_html
    )
    requests = [r for r in spider.parse(response) if isinstance(r, Request)]
    assert not any("page=2" in r.url for r in requests)


def test_product_id_deterministic(jumia_listing_html):
    spider = JumiaSpider()
    response = fake_response(
        "https://www.jumia.ma/ordinateurs-portables/", jumia_listing_html
    )
    items1 = [r for r in spider.parse(response) if isinstance(r, PriceItem)]

    spider2 = JumiaSpider()
    items2 = [r for r in spider2.parse(response) if isinstance(r, PriceItem)]

    assert items1[0]["product_id"] == items2[0]["product_id"]
