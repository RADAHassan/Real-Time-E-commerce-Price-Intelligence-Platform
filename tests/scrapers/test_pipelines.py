"""
Unit tests for the three item pipelines.
ValidationPipeline and JsonOutputPipeline are tested directly.
NiFiHttpPipeline is tested with a mocked requests.Session.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scrapers.items import PriceItem
from scrapers.pipelines import JsonOutputPipeline, NiFiHttpPipeline, ValidationPipeline
from scrapy.exceptions import DropItem


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def valid_item():
    return PriceItem(
        product_id="abc123",
        source="books.toscrape.com",
        url="https://books.toscrape.com/catalogue/book_1/index.html",
        title="Test Book",
        price=19.99,
        currency="GBP",
        rating=4.0,
        availability="In stock",
        category="Fiction",
        image_url="https://books.toscrape.com/media/cover.jpg",
        scraped_at="2026-04-24T12:00:00+00:00",
    )


@pytest.fixture
def mock_spider():
    spider = MagicMock()
    spider.name = "books_spider"
    return spider


# ---------------------------------------------------------------------------
# ValidationPipeline
# ---------------------------------------------------------------------------


class TestValidationPipeline:
    def setup_method(self):
        self.pipeline = ValidationPipeline()

    def test_valid_item_passes(self, valid_item, mock_spider):
        result = self.pipeline.process_item(valid_item, mock_spider)
        assert result is valid_item

    def test_missing_title_drops(self, valid_item, mock_spider):
        valid_item["title"] = ""
        with pytest.raises(DropItem, match="title"):
            self.pipeline.process_item(valid_item, mock_spider)

    def test_missing_price_drops(self, valid_item, mock_spider):
        valid_item["price"] = None
        with pytest.raises(DropItem):
            self.pipeline.process_item(valid_item, mock_spider)

    def test_non_numeric_price_drops(self, valid_item, mock_spider):
        valid_item["price"] = "not-a-number"
        with pytest.raises(DropItem):
            self.pipeline.process_item(valid_item, mock_spider)

    def test_negative_price_drops(self, valid_item, mock_spider):
        valid_item["price"] = -5.0
        with pytest.raises(DropItem, match="Negative"):
            self.pipeline.process_item(valid_item, mock_spider)

    def test_zero_price_is_valid(self, valid_item, mock_spider):
        valid_item["price"] = 0.0
        result = self.pipeline.process_item(valid_item, mock_spider)
        assert result["price"] == 0.0

    def test_missing_product_id_drops(self, valid_item, mock_spider):
        valid_item["product_id"] = ""
        with pytest.raises(DropItem):
            self.pipeline.process_item(valid_item, mock_spider)


# ---------------------------------------------------------------------------
# JsonOutputPipeline
# ---------------------------------------------------------------------------


class TestJsonOutputPipeline:
    def test_writes_jsonl_file(self, valid_item, mock_spider):
        pipeline = JsonOutputPipeline()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Patch Path so output lands in tmpdir
            with patch("scrapers.pipelines.Path") as MockPath:
                output_dir = Path(tmpdir) / "books_spider"
                MockPath.return_value = output_dir
                output_dir.mkdir(parents=True, exist_ok=True)

                # Manually exercise open/write/close
                pipeline._handles["books_spider"] = (output_dir / "out.jsonl").open(
                    "w", encoding="utf-8"
                )
                pipeline.process_item(valid_item, mock_spider)
                pipeline.close_spider(mock_spider)

                written = (output_dir / "out.jsonl").read_text()
                data = json.loads(written.strip())
                assert data["title"] == "Test Book"
                assert data["price"] == 19.99

    def test_item_passes_through(self, valid_item, mock_spider):
        pipeline = JsonOutputPipeline()
        pipeline._handles["books_spider"] = MagicMock()
        result = pipeline.process_item(valid_item, mock_spider)
        assert result is valid_item


# ---------------------------------------------------------------------------
# NiFiHttpPipeline
# ---------------------------------------------------------------------------


class TestNiFiHttpPipeline:
    def test_no_op_when_disabled(self, valid_item, mock_spider):
        pipeline = NiFiHttpPipeline(nifi_url="http://nifi:8080/listener", push_enabled=False)
        result = pipeline.process_item(valid_item, mock_spider)
        assert result is valid_item  # passes through untouched

    def test_no_op_when_url_empty(self, valid_item, mock_spider):
        pipeline = NiFiHttpPipeline(nifi_url="", push_enabled=True)
        result = pipeline.process_item(valid_item, mock_spider)
        assert result is valid_item

    def test_posts_when_enabled(self, valid_item, mock_spider):
        pipeline = NiFiHttpPipeline(nifi_url="http://nifi:8080/listener", push_enabled=True)
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch.object(pipeline._session, "post", return_value=mock_response) as mock_post:
            pipeline.process_item(valid_item, mock_spider)

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs[0][0] == "http://nifi:8080/listener"
        payload = json.loads(call_kwargs[1]["data"])
        assert payload["title"] == "Test Book"

    def test_network_failure_does_not_raise(self, valid_item, mock_spider):
        pipeline = NiFiHttpPipeline(nifi_url="http://nifi:8080/listener", push_enabled=True)

        with patch.object(pipeline._session, "post", side_effect=ConnectionError("refused")):
            result = pipeline.process_item(valid_item, mock_spider)

        assert result is valid_item  # crawl must continue despite NiFi being down
