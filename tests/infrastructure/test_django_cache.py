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

    def test_get_degrades_gracefully_on_connection_error(self) -> None:
        """get() zwraca None i nie wychodzi, gdy Redis niedostępny (AUDYT-114)."""
        adapter = DjangoCacheAdapter()
        with patch("infrastructure.adapters.django_cache.cache") as mock_cache:
            mock_cache.get.side_effect = ConnectionError("redis down")
            assert adapter.get("test_key") is None

    def test_get_degrades_gracefully_on_timeout(self) -> None:
        """get() zwraca None przy TimeoutError (AUDYT-114)."""
        adapter = DjangoCacheAdapter()
        with patch("infrastructure.adapters.django_cache.cache") as mock_cache:
            mock_cache.get.side_effect = TimeoutError("slow")
            assert adapter.get("test_key") is None

    def test_set_degrades_gracefully_on_connection_error(self) -> None:
        """set() nie wychodzi, gdy Redis niedostępny (AUDYT-114)."""
        adapter = DjangoCacheAdapter()
        with patch("infrastructure.adapters.django_cache.cache") as mock_cache:
            mock_cache.set.side_effect = ConnectionError("redis down")
            adapter.set("test_key", "value", 300)

    def test_set_degrades_gracefully_on_timeout(self) -> None:
        """set() nie wychodzi przy TimeoutError (AUDYT-114)."""
        adapter = DjangoCacheAdapter()
        with patch("infrastructure.adapters.django_cache.cache") as mock_cache:
            mock_cache.set.side_effect = TimeoutError("slow")
            adapter.set("test_key", "value", 300)

    def test_delete_degrades_gracefully_on_connection_error(self) -> None:
        """delete() nie wychodzi, gdy Redis niedostępny (AUDYT-114)."""
        adapter = DjangoCacheAdapter()
        with patch("infrastructure.adapters.django_cache.cache") as mock_cache:
            mock_cache.delete.side_effect = ConnectionError("redis down")
            adapter.delete("test_key")
