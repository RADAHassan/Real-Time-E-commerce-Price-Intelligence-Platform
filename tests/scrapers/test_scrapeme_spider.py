"""
Unit tests for ScrapemeSpider.
All tests use fake HTML — no network calls are made.
"""

import pytest
from scrapy.http import Request

from scrapers.spiders.scrapeme_spider import ScrapemeSpider, _parse_price, _parse_wc_rating
from scrapers.items import PriceItem

from tests.scrapers.conftest import fake_response


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("£63.00", 63.0),
        ("£1,500.00", 1500.0),
        ("€29.99", 29.99),
        ("", 0.0),
    ],
)
def test_parse_price(raw, expected):
    assert _parse_price(raw) == pytest.approx(expected)


@pytest.mark.parametrize(
    "label, expected",
    [
        ("4.50 out of 5", 4.5),
        ("3.00 out of 5", 3.0),
        ("", None),
        ("not-a-rating", None),
    ],
)
def test_parse_wc_rating(label, expected):
    result = _parse_wc_rating(label)
    if expected is None:
        assert result is None
    else:
        assert result == pytest.approx(expected)


# ---------------------------------------------------------------------------
# Listing page
# ---------------------------------------------------------------------------


def test_listing_yields_detail_requests(scrapeme_listing_html):
    spider = ScrapemeSpider()
    response = fake_response("https://scrapeme.live/shop/page/1/", scrapeme_listing_html)

    results = list(spider.parse(response))
    requests = [r for r in results if isinstance(r, Request) and "page" not in r.url]
    assert len(requests) == 2


def test_listing_follows_next_page(scrapeme_listing_html):
    spider = ScrapemeSpider()
    response = fake_response("https://scrapeme.live/shop/page/1/", scrapeme_listing_html)

    results = list(spider.parse(response))
    next_reqs = [r for r in results if isinstance(r, Request) and "page/2" in r.url]
    assert len(next_reqs) == 1


def test_listing_stops_at_max_pages():
    spider = ScrapemeSpider(max_pages=1)
    html = """
    <html><body>
      <ul class="products">
        <li class="product">
          <a class="woocommerce-loop-product__link"
             href="https://scrapeme.live/shop/bulbasaur/">Bulbasaur</a>
        </li>
      </ul>
      <a class="next page-numbers" href="https://scrapeme.live/shop/page/2/">→</a>
    </body></html>
    """
    response = fake_response("https://scrapeme.live/shop/page/1/", html)
    results = list(spider.parse(response))
    next_reqs = [r for r in results if isinstance(r, Request) and "page/2" in r.url]
    assert len(next_reqs) == 0


# ---------------------------------------------------------------------------
# Detail page
# ---------------------------------------------------------------------------


def test_detail_yields_price_item(scrapeme_detail_html):
    spider = ScrapemeSpider()
    url = "https://scrapeme.live/shop/bulbasaur/"
    response = fake_response(url, scrapeme_detail_html)

    items = [r for r in spider.parse_product(response) if isinstance(r, PriceItem)]
    assert len(items) == 1
    item = items[0]

    assert item["title"] == "Bulbasaur"
    assert item["price"] == pytest.approx(63.0)
    assert item["currency"] == "GBP"
    assert item["rating"] == pytest.approx(4.5)
    assert item["availability"] == "In Stock"
    assert item["category"] == "Pokémon"
    assert item["source"] == "scrapeme.live"


def test_detail_out_of_stock():
    spider = ScrapemeSpider()
    url = "https://scrapeme.live/shop/mew/"
    html = """
    <html><body>
      <h1 class="product_title entry-title">Mew</h1>
      <p class="price">
        <span class="woocommerce-Price-amount amount">
          <bdi><span class="woocommerce-Price-currencySymbol">£</span>999.00</bdi>
        </span>
      </p>
      <p class="stock out-of-stock">Out of stock</p>
      <span class="posted_in"><a href="/category/legendary/">Legendary</a></span>
    </body></html>
    """
    response = fake_response(url, html)
    item = next(spider.parse_product(response))
    assert item["availability"] == "Out of Stock"
