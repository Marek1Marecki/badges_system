"""Testy dla modeli Django w obszarze Turysty."""

from unittest.mock import MagicMock

from apps.tourists.models import AscentLog, TouristProfile, UserBadgeProgress, profile_directory_path


class TestProfileDirectoryPath:
    """Testy funkcji profile_directory_path."""

    def test_returns_correct_path(self):
        """Zwraca ścieżkę z profile_id i datą."""
        instance = MagicMock()
        instance.profile_id = 42
        instance.ascent_date = "2024-01-15"
        filename = "photo.jpg"

        result = profile_directory_path(instance, filename)

        assert result == "ascents/profile_42/2024-01-15_photo.jpg"

    def test_handles_special_characters_in_filename(self):
        """Obsługuje specjalne znaki w nazwie pliku."""
        instance = MagicMock()
        instance.profile_id = 1
        instance.ascent_date = "2024-01-15"
        filename = "my photo (1).jpg"

        result = profile_directory_path(instance, filename)

        assert "ascents/profile_1/" in result
        assert "2024-01-15_my photo (1).jpg" in result


class TestTouristProfileStr:
    """Testy metody __str__ modelu TouristProfile."""

    def test_str_main_profile(self):
        """Zwraca nazwę z oznaczeniem [GŁÓWNY] dla głównego profilu."""
        profile = MagicMock()
        profile.is_main_profile = True
        profile.nickname = "Test"
        profile.user.email = "test@example.com"

        result = TouristProfile.__str__(profile)

        assert "Test" in result
        assert "test@example.com" in result
        assert "[GŁÓWNY]" in result

    def test_str_regular_profile(self):
        """Zwraca nazwę bez oznaczenia dla zwykłego profilu."""
        profile = MagicMock()
        profile.is_main_profile = False
        profile.nickname = "Dziecko"
        profile.user.email = "dziecko@example.com"

        result = TouristProfile.__str__(profile)

        assert "Dziecko" in result
        assert "dziecko@example.com" in result
        assert "[GŁÓWNY]" not in result


class TestAscentLogStr:
    """Testy metody __str__ modelu AscentLog."""

    def test_str_returns_formatted_string(self):
        """Zwraca sformatowany ciąg z profilem, szczytem i datą."""
        profile = MagicMock()
        profile.nickname = "Test"
        peak = MagicMock()
        peak.name = "Rysy"
        ascent = MagicMock()
        ascent.profile = profile
        ascent.peak = peak
        ascent.ascent_date = "2024-01-15"

        result = AscentLog.__str__(ascent)

        assert "Test" in result
        assert "Rysy" in result
        assert "2024-01-15" in result


class TestUserBadgeProgressStr:
    """Testy metody __str__ modelu UserBadgeProgress."""

    def test_str_with_version(self):
        """Zwraca sformatowany ciąg gdy istnieje wersja."""
        profile = MagicMock()
        profile.nickname = "Test"
        badge = MagicMock()
        badge.code = "KGP"
        version = MagicMock()
        version.version_code = "v2024"

        progress = MagicMock()
        progress.profile = profile
        progress.badge = badge
        progress.version = version
        progress.cycle_number = 1
        progress.domain_status = "IN_PROGRESS"

        result = UserBadgeProgress.__str__(progress)

        assert "Test" in result
        assert "KGP" in result
        assert "v2024" in result
        assert "Cykl 1" in result

    def test_str_without_version(self):
        """Zwraca sformatowany ciąg gdy brak wersji."""
        profile = MagicMock()
        profile.nickname = "Test"
        badge = MagicMock()
        badge.code = "KGP"

        progress = MagicMock()
        progress.profile = profile
        progress.badge = badge
        progress.version = None
        progress.cycle_number = 2
        progress.domain_status = "COMPLETED"

        result = UserBadgeProgress.__str__(progress)

        assert "Test" in result
        assert "KGP" in result
        assert "BRAK (Oczekuje)" in result
        assert "Cykl 2" in result
        assert "COMPLETED" in result
