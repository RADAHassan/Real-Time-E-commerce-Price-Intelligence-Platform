"""
Unit tests for BooksSpider.
All tests use fake HTML — no network calls are made.
"""

import pytest
from scrapy.http import Request, TextResponse

from scrapers.spiders.books_spider import BooksSpider, _parse_price
from scrapers.items import PriceItem

from tests.scrapers.conftest import fake_response


# ---------------------------------------------------------------------------
# _parse_price helper
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("£51.77", 51.77),
        ("Â£12.99", 12.99),   # encoding artifact seen on some pages
        ("£1,234.56", 1234.56),
        ("0", 0.0),
        ("not-a-price", 0.0),
    ],
)
def test_parse_price(raw, expected):
    assert _parse_price(raw) == pytest.approx(expected)


# ---------------------------------------------------------------------------
# Listing page
# ---------------------------------------------------------------------------


def test_listing_yields_detail_requests(books_listing_html):
    spider = BooksSpider()
    response = fake_response("https://books.toscrape.com/catalogue/page-1.html", books_listing_html)

    results = list(spider.parse(response))

    # Exclude the next-page request — only count detail page requests
    detail_requests = [r for r in results if isinstance(r, Request) and "index.html" in r.url]
    assert len(detail_requests) == 2, "Should yield one Request per book article"
    assert all("toscrape.com" in r.url for r in detail_requests)


def test_listing_follows_next_page(books_listing_html):
    spider = BooksSpider()
    response = fake_response("https://books.toscrape.com/catalogue/page-1.html", books_listing_html)

    results = list(spider.parse(response))
    next_requests = [r for r in results if isinstance(r, Request) and "page-2" in r.url]
    assert len(next_requests) == 1


def test_listing_stops_at_max_pages():
    spider = BooksSpider(max_pages=1)
    html = """
    <html><body>
      <article class="product_pod">
        <h3><a href="../book_1/index.html">Book</a></h3>
      </article>
      <li class="next"><a href="page-2.html">next</a></li>
    </body></html>
    """
    response = fake_response("https://books.toscrape.com/catalogue/page-1.html", html)
    results = list(spider.parse(response))
    next_page_reqs = [r for r in results if isinstance(r, Request) and "page-2" in r.url]
    assert len(next_page_reqs) == 0, "Should not follow next page when max_pages reached"


# ---------------------------------------------------------------------------
# Detail page
# ---------------------------------------------------------------------------


def test_detail_yields_price_item(books_detail_html):
    spider = BooksSpider()
    url = "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
    response = fake_response(url, books_detail_html)

    items = [r for r in spider.parse_book(response) if isinstance(r, PriceItem)]
    assert len(items) == 1
    item = items[0]

    assert item["title"] == "A Light in the Attic"
    assert item["price"] == pytest.approx(51.77)
    assert item["currency"] == "GBP"
    assert item["rating"] == pytest.approx(3.0)
    assert item["category"] == "Poetry"
    assert item["source"] == "books.toscrape.com"
    assert item["product_id"] != ""
    assert "In stock" in item["availability"]


def test_detail_product_id_is_deterministic(books_detail_html):
    spider = BooksSpider()
    url = "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
    response = fake_response(url, books_detail_html)

    item1 = next(spider.parse_book(response))
    item2 = next(spider.parse_book(response))
    assert item1["product_id"] == item2["product_id"]


def test_detail_scraped_at_is_iso8601(books_detail_html):
    from datetime import datetime

    spider = BooksSpider()
    url = "https://books.toscrape.com/catalogue/some_book/index.html"
    response = fake_response(url, books_detail_html)

    item = next(spider.parse_book(response))
    # Should not raise
    datetime.fromisoformat(item["scraped_at"])
