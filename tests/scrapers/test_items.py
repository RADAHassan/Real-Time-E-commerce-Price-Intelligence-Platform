"""Tests for PriceItem — ensures the item schema is correctly defined."""

import pytest
from scrapers.items import PriceItem


def test_price_item_all_fields():
    item = PriceItem(
        product_id="abc123",
        source="books.toscrape.com",
        url="https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
        title="A Light in the Attic",
        price=51.77,
        currency="GBP",
        rating=3.0,
        availability="In stock",
        category="Poetry",
        image_url="https://books.toscrape.com/media/cache/cover.jpg",
        scraped_at="2026-04-24T12:00:00+00:00",
    )
    assert item["product_id"] == "abc123"
    assert item["price"] == 51.77
    assert item["currency"] == "GBP"


def test_price_item_optional_fields_can_be_none():
    item = PriceItem(
        product_id="xyz",
        source="scrapeme.live",
        url="https://scrapeme.live/shop/bulbasaur/",
        title="Bulbasaur",
        price=63.0,
        currency="GBP",
        scraped_at="2026-04-24T12:00:00+00:00",
    )
    assert item.get("rating") is None
    assert item.get("image_url") is None


def test_price_item_rejects_unknown_field():
    with pytest.raises(KeyError):
        PriceItem(nonexistent_field="oops")
