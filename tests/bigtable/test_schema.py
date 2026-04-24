"""
Unit tests for bigtable/schema.py.
The google-cloud-bigtable Client is fully mocked — no emulator needed.
"""

from unittest.mock import MagicMock, call, patch

import pytest

from bigtable.schema import COLUMN_FAMILIES, TABLE_ID, create_schema, drop_schema


@pytest.fixture
def mock_bigtable_stack():
    """Returns (mock_client, mock_instance, mock_table, mock_cf) pre-wired."""
    mock_cf = MagicMock()
    mock_table = MagicMock()
    mock_table.column_family.return_value = mock_cf
    mock_instance = MagicMock()
    mock_instance.table.return_value = mock_table
    mock_client = MagicMock()
    mock_client.instance.return_value = mock_instance
    return mock_client, mock_instance, mock_table, mock_cf


class TestCreateSchema:
    def test_creates_table_and_column_families(self, mock_bigtable_stack):
        mock_client, mock_instance, mock_table, mock_cf = mock_bigtable_stack
        mock_table.exists.return_value = False

        with patch("bigtable.schema.bigtable.Client", return_value=mock_client):
            create_schema("my-project", "my-instance")

        mock_table.create.assert_called_once()
        # One column_family() call per family, then cf.create()
        assert mock_table.column_family.call_count == len(COLUMN_FAMILIES)
        assert mock_cf.create.call_count == len(COLUMN_FAMILIES)

    def test_creates_all_expected_families(self, mock_bigtable_stack):
        mock_client, _, mock_table, _ = mock_bigtable_stack
        mock_table.exists.return_value = False

        with patch("bigtable.schema.bigtable.Client", return_value=mock_client):
            create_schema("proj", "inst")

        called_families = {c.args[0] for c in mock_table.column_family.call_args_list}
        assert called_families == set(COLUMN_FAMILIES.keys())

    def test_skips_creation_if_table_exists(self, mock_bigtable_stack):
        mock_client, _, mock_table, mock_cf = mock_bigtable_stack
        mock_table.exists.return_value = True

        with patch("bigtable.schema.bigtable.Client", return_value=mock_client):
            create_schema("proj", "inst")

        mock_table.create.assert_not_called()
        mock_cf.create.assert_not_called()

    def test_uses_correct_table_id(self, mock_bigtable_stack):
        mock_client, mock_instance, mock_table, _ = mock_bigtable_stack
        mock_table.exists.return_value = False

        with patch("bigtable.schema.bigtable.Client", return_value=mock_client):
            create_schema("proj", "inst")

        mock_instance.table.assert_called_once_with(TABLE_ID)

    def test_custom_table_id(self, mock_bigtable_stack):
        mock_client, mock_instance, mock_table, _ = mock_bigtable_stack
        mock_table.exists.return_value = False

        with patch("bigtable.schema.bigtable.Client", return_value=mock_client):
            create_schema("proj", "inst", table_id="custom_prices")

        mock_instance.table.assert_called_once_with("custom_prices")


class TestDropSchema:
    def test_deletes_existing_table(self, mock_bigtable_stack):
        mock_client, _, mock_table, _ = mock_bigtable_stack
        mock_table.exists.return_value = True

        with patch("bigtable.schema.bigtable.Client", return_value=mock_client):
            drop_schema("proj", "inst")

        mock_table.delete.assert_called_once()

    def test_skips_if_table_does_not_exist(self, mock_bigtable_stack):
        mock_client, _, mock_table, _ = mock_bigtable_stack
        mock_table.exists.return_value = False

        with patch("bigtable.schema.bigtable.Client", return_value=mock_client):
            drop_schema("proj", "inst")

        mock_table.delete.assert_not_called()
