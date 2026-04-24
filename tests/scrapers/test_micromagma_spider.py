"""Tests for MicromagmaSpider — aucun appel réseau."""

import pytest
from scrapy.http import Request

from scrapers.items import PriceItem
from scrapers.spiders.micromagma_spider import MicromagmaSpider
from tests.scrapers.conftest import fake_response


@pytest.fixture
def micromagma_listing_html():
    return """
    <html><body>
      <nav class="breadcrumb">
        <ol>
          <li><span>Accueil</span></li>
          <li><span>Ordinateurs Portables</span></li>
        </ol>
      </nav>
      <section id="products">
        <article class="product-miniature">
          <h2 class="product-title">
            <a href="https://www.micromagma.ma/laptops/hp-255-g9.html">
              HP 255 G9 Ryzen 5 8Go 256Go SSD
            </a>
          </h2>
          <span class="price">5 299,00 DH</span>
          <img class="img-fluid"
               src="https://www.micromagma.ma/img/hp-255-g9.jpg" alt="HP">
        </article>
        <article class="product-miniature">
          <h2 class="product-title">
            <a href="https://www.micromagma.ma/laptops/lenovo-v15.html">
              Lenovo V15 G3 Core i3 8Go 512Go SSD
            </a>
          </h2>
          <span class="price">4 199,00 DH</span>
          <span class="product-unavailable">Rupture de stock</span>
        </article>
        <article class="product-miniature">
          <h2 class="product-title">
            <a href="https://www.micromagma.ma/laptops/sans-prix.html">Sans prix</a>
          </h2>
          <span class="price"></span>
        </article>
      </section>
      <a rel="next" href="https://www.micromagma.ma/ordinateurs-portables?page=2">Suivant</a>
    </body></html>
    """


@pytest.fixture
def micromagma_detail_html():
    return """
    <html><body>
      <nav class="breadcrumb">
        <ol>
          <li><span>Accueil</span></li>
          <li><span>Ordinateurs Portables</span></li>
          <li><span>HP 255 G9</span></li>
        </ol>
      </nav>
      <div class="product-prices">
        <span class="price">5 099,00 DH</span>
      </div>
      <img class="js-qv-product-cover"
           src="https://www.micromagma.ma/img/hi-res/hp-255-g9.jpg" alt="HP">
    </body></html>
    """


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------


def test_listing_yields_detail_requests(micromagma_listing_html):
    spider = MicromagmaSpider()
    response = fake_response(
        "https://www.micromagma.ma/ordinateurs-portables", micromagma_listing_html
    )
    results = list(spider.parse(response))
    detail_reqs = [r for r in results if isinstance(r, Request) and r.url.endswith(".html")]
    assert len(detail_reqs) == 2


def test_listing_skips_zero_price(micromagma_listing_html):
    spider = MicromagmaSpider()
    response = fake_response(
        "https://www.micromagma.ma/ordinateurs-portables", micromagma_listing_html
    )
    results = list(spider.parse(response))
    sans_prix = [r for r in results if isinstance(r, Request) and "sans-prix" in r.url]
    assert len(sans_prix) == 0


def test_listing_follows_next_page(micromagma_listing_html):
    spider = MicromagmaSpider()
    response = fake_response(
        "https://www.micromagma.ma/ordinateurs-portables", micromagma_listing_html
    )
    results = list(spider.parse(response))
    next_reqs = [r for r in results if isinstance(r, Request) and "page=2" in r.url]
    assert len(next_reqs) == 1


def test_listing_stops_at_max_pages(micromagma_listing_html):
    spider = MicromagmaSpider(max_pages=1)
    response = fake_response(
        "https://www.micromagma.ma/ordinateurs-portables", micromagma_listing_html
    )
    results = list(spider.parse(response))
    next_reqs = [r for r in results if isinstance(r, Request) and "page=2" in r.url]
    assert len(next_reqs) == 0


def test_listing_out_of_stock_detected(micromagma_listing_html):
    """Le partial_item transmis à _parse_detail doit déjà signaler le stock."""
    spider = MicromagmaSpider()
    response = fake_response(
        "https://www.micromagma.ma/ordinateurs-portables", micromagma_listing_html
    )
    results = list(spider.parse(response))
    detail_reqs = [r for r in results if isinstance(r, Request) and r.url.endswith(".html")]
    lenovo_req = next(r for r in detail_reqs if "lenovo" in r.url)
    assert lenovo_req.cb_kwargs["partial_item"]["availability"] == "Out of Stock"


# ---------------------------------------------------------------------------
# Detail page
# ---------------------------------------------------------------------------


def test_detail_updates_price(micromagma_detail_html):
    spider = MicromagmaSpider()
    url = "https://www.micromagma.ma/laptops/hp-255-g9.html"
    partial = PriceItem(
        product_id="abc",
        source="micromagma.ma",
        url=url,
        title="HP 255 G9 Ryzen 5 8Go 256Go SSD",
        price=5299.0,
        currency="MAD",
        rating=None,
        availability="In Stock",
        category="Ordinateurs Portables",
        image_url="",
        scraped_at="2026-04-24T12:00:00+00:00",
    )
    response = fake_response(url, micromagma_detail_html)
    item = next(spider._parse_detail(response, partial))

    assert item["price"] == pytest.approx(5099.0)
    assert item["category"] == "Ordinateurs Portables"
    assert "hi-res" in item["image_url"]
    assert item["source"] == "micromagma.ma"
    assert item["currency"] == "MAD"
