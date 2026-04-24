"""
Unit tests for bigtable/client.py.
BigtableClient accepts _table= for dependency injection — no emulator needed.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, call, patch

import pytest

from bigtable.client import BigtableClient, _make_row_key, _cell_bytes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_fake_row(row_key: str, cells: dict) -> MagicMock:
    """Build a fake Bigtable Row object with the given cells dict.

    cells format: {b"cf_id": {b"col": [MagicMock(value=b"val")]}}
    """
    row = MagicMock()
    row.row_key = row_key.encode()
    row.cells = cells
    return row


def _fake_cell(value: str) -> list:
    cell = MagicMock()
    cell.value = value.encode()
    return [cell]


@pytest.fixture
def sample_item():
    return {
        "product_id": "abc123def456abc123def456abc12345",
        "source": "jumia.ma",
        "url": "https://www.jumia.ma/hp-pavilion.html",
        "title": "HP Pavilion 15",
        "price": 4299.0,
        "currency": "MAD",
        "rating": 4.0,
        "availability": "In Stock",
        "category": "Ordinateurs Portables",
        "image_url": "https://img.jumia.ma/hp.jpg",
        "scraped_at": "2026-04-24T12:00:00+00:00",
    }


@pytest.fixture
def mock_table():
    return MagicMock()


@pytest.fixture
def client(mock_table):
    return BigtableClient("proj", "inst", _table=mock_table)


# ---------------------------------------------------------------------------
# _make_row_key
# ---------------------------------------------------------------------------


def test_make_row_key_format():
    key = _make_row_key("abc123").decode()
    parts = key.split("#")
    assert len(parts) == 2
    assert parts[0] == "abc123"
    assert len(parts[1]) == 19   # zero-padded to 19 digits
    assert parts[1].isdigit()


def test_make_row_key_is_decreasing():
    """Two keys generated in sequence should be in descending order (latest first)."""
    import time

    k1 = _make_row_key("prod")
    time.sleep(0.01)
    k2 = _make_row_key("prod")
    # k1 was created earlier → higher reversed_ts → sorts BEFORE k2 in byte order
    assert k1 > k2


def test_make_row_key_same_product_same_prefix():
    k1 = _make_row_key("prod_abc")
    k2 = _make_row_key("prod_abc")
    assert k1.split(b"#")[0] == k2.split(b"#")[0]


# ---------------------------------------------------------------------------
# _cell_bytes
# ---------------------------------------------------------------------------


def test_cell_bytes_float():
    assert _cell_bytes(4299.0) == b"4299.0"


def test_cell_bytes_none():
    assert _cell_bytes(None) == b""


def test_cell_bytes_string():
    assert _cell_bytes("MAD") == b"MAD"


# ---------------------------------------------------------------------------
# BigtableClient.write_price_item
# ---------------------------------------------------------------------------


class TestWritePriceItem:
    def test_calls_direct_row(self, client, mock_table, sample_item):
        mock_row = MagicMock()
        mock_table.direct_row.return_value = mock_row

        client.write_price_item(sample_item)

        mock_table.direct_row.assert_called_once()
        # Row key must start with product_id
        row_key_arg = mock_table.direct_row.call_args[0][0]
        assert row_key_arg.startswith(sample_item["product_id"].encode())

    def test_commits_row(self, client, mock_table, sample_item):
        mock_row = MagicMock()
        mock_table.direct_row.return_value = mock_row

        client.write_price_item(sample_item)
        mock_row.commit.assert_called_once()

    def test_writes_price_cf_columns(self, client, mock_table, sample_item):
        mock_row = MagicMock()
        mock_table.direct_row.return_value = mock_row

        client.write_price_item(sample_item)

        set_cell_calls = mock_row.set_cell.call_args_list
        cf_col_pairs = [(c.args[0], c.args[1]) for c in set_cell_calls]
        assert ("price_cf", "price") in cf_col_pairs
        assert ("price_cf", "currency") in cf_col_pairs
        assert ("price_cf", "availability") in cf_col_pairs

    def test_writes_metadata_cf_columns(self, client, mock_table, sample_item):
        mock_row = MagicMock()
        mock_table.direct_row.return_value = mock_row

        client.write_price_item(sample_item)

        set_cell_calls = mock_row.set_cell.call_args_list
        cf_col_pairs = [(c.args[0], c.args[1]) for c in set_cell_calls]
        assert ("metadata_cf", "title") in cf_col_pairs
        assert ("metadata_cf", "source") in cf_col_pairs
        assert ("metadata_cf", "scraped_at") in cf_col_pairs

    def test_returns_row_key_string(self, client, mock_table, sample_item):
        mock_row = MagicMock()
        mock_table.direct_row.return_value = mock_row

        result = client.write_price_item(sample_item)

        assert isinstance(result, str)
        assert sample_item["product_id"] in result

    def test_raises_on_missing_product_id(self, client, mock_table):
        with pytest.raises(ValueError, match="product_id"):
            client.write_price_item({"title": "test", "product_id": ""})


# ---------------------------------------------------------------------------
# BigtableClient.get_latest_price
# ---------------------------------------------------------------------------


class TestGetLatestPrice:
    def _make_price_row(self, product_id: str, price: str = "4299.0") -> MagicMock:
        return _make_fake_row(
            f"{product_id}#9999999999999999999",
            {
                b"price_cf": {
                    b"price": _fake_cell(price),
                    b"currency": _fake_cell("MAD"),
                    b"availability": _fake_cell("In Stock"),
                },
                b"metadata_cf": {
                    b"title": _fake_cell("HP Pavilion"),
                    b"source": _fake_cell("jumia.ma"),
                    b"url": _fake_cell("https://jumia.ma/hp"),
                    b"category": _fake_cell("Laptops"),
                    b"image_url": _fake_cell(""),
                    b"rating": _fake_cell("4.0"),
                    b"scraped_at": _fake_cell("2026-04-24T12:00:00+00:00"),
                },
            },
        )

    def test_returns_none_when_no_rows(self, client, mock_table):
        mock_table.read_rows.return_value = iter([])
        result = client.get_latest_price("abc123")
        assert result is None

    def test_returns_dict_with_price_as_float(self, client, mock_table):
        product_id = "abc123def456abc123def456abc12345"
        mock_table.read_rows.return_value = iter([self._make_price_row(product_id)])

        result = client.get_latest_price(product_id)

        assert result is not None
        assert result["price"] == pytest.approx(4299.0)
        assert isinstance(result["price"], float)

    def test_scan_range_uses_product_prefix(self, client, mock_table):
        mock_table.read_rows.return_value = iter([])
        client.get_latest_price("abc123")

        call_kwargs = mock_table.read_rows.call_args[1]
        assert call_kwargs["start_key"].startswith(b"abc123#")
        assert call_kwargs["limit"] == 1

    def test_row_key_in_result(self, client, mock_table):
        product_id = "abc123def456abc123def456abc12345"
        mock_table.read_rows.return_value = iter([self._make_price_row(product_id)])

        result = client.get_latest_price(product_id)
        assert "row_key" in result


# ---------------------------------------------------------------------------
# BigtableClient._row_to_dict
# ---------------------------------------------------------------------------


class TestRowToDict:
    def test_converts_price_to_float(self):
        row = _make_fake_row(
            "prod#123",
            {b"price_cf": {b"price": _fake_cell("1234.56")}},
        )
        result = BigtableClient._row_to_dict(row)
        assert result["price"] == pytest.approx(1234.56)
        assert isinstance(result["price"], float)

    def test_converts_rating_to_float(self):
        row = _make_fake_row(
            "prod#123",
            {b"metadata_cf": {b"rating": _fake_cell("3.5")}},
        )
        result = BigtableClient._row_to_dict(row)
        assert result["rating"] == pytest.approx(3.5)

    def test_keeps_empty_rating_as_string(self):
        row = _make_fake_row(
            "prod#123",
            {b"metadata_cf": {b"rating": _fake_cell("")}},
        )
        result = BigtableClient._row_to_dict(row)
        assert result["rating"] == ""

    def test_row_key_always_present(self):
        row = _make_fake_row("prod#9999", {})
        result = BigtableClient._row_to_dict(row)
        assert result["row_key"] == "prod#9999"
