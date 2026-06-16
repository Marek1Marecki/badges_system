"""Testy dla DjangoCacheAdapter."""

from unittest.mock import patch

from infrastructure.adapters.django_cache import DjangoCacheAdapter


class TestDjangoCacheAdapter:
    """Testy klasy DjangoCacheAdapter."""

    def test_set(self):
        """Test metody set."""
        adapter = DjangoCacheAdapter()

        with patch("infrastructure.adapters.django_cache.cache") as mock_cache:
            adapter.set("test_key", "test_value", 300)
            mock_cache.set.assert_called_once_with("test_key", "test_value", timeout=300)

    def test_get(self):
        """Test metody get."""
        adapter = DjangoCacheAdapter()

        with patch("infrastructure.adapters.django_cache.cache") as mock_cache:
            mock_cache.get.return_value = "test_value"
            result = adapter.get("test_key")
            mock_cache.get.assert_called_once_with("test_key")
            assert result == "test_value"

    def test_get_returns_none_when_cache_miss(self):
        """Test że get zwraca None gdy brak wartości w cache."""
        adapter = DjangoCacheAdapter()

        with patch("infrastructure.adapters.django_cache.cache") as mock_cache:
            mock_cache.get.return_value = None
            result = adapter.get("test_key")
            assert result is None

    def test_delete(self):
        """Test metody delete."""
        adapter = DjangoCacheAdapter()

        with patch("infrastructure.adapters.django_cache.cache") as mock_cache:
            adapter.delete("test_key")
            mock_cache.delete.assert_called_once_with("test_key")

    def test_set_with_various_types(self):
        """Test set z różnymi typami danych."""
        adapter = DjangoCacheAdapter()

        test_values = [
            ("string_key", "string_value"),
            ("int_key", 123),
            ("dict_key", {"key": "value"}),
            ("list_key", [1, 2, 3]),
        ]

        with patch("infrastructure.adapters.django_cache.cache") as mock_cache:
            for key, value in test_values:
                adapter.set(key, value, 300)
                mock_cache.set.assert_called_with(key, value, timeout=300)
