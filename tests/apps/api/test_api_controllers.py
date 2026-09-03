"""Testy kontrlerów (Controller Contract) dla REST API turysty (Faza C).

Strategia: RequestFactory + MagicMock user + request.app_container.
Views używają request.app_container (ustawianego przez ContainerMiddleware),
więc factory automatycznie wstrzykuje kontener DI do każdego requestu.

Uwaga (AUDYT-080): Nie są to testy *prawdziwie integracyjne* — mockują
UseCase'y przez request.app_container. Dlatego nazwa odzwierciedla
rolę (Controller Contract), a nie fale testów integracyjnych.
Prawdziwe testy E2E realizowane są w testach Playwright (tests/e2e/).
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from tests.fakes.clock import FakeClock

TEST_TODAY = str(FakeClock.DEFAULT_TIME.date())


class UseCaseContainer:
    def __init__(self, cases: dict):
        self._cases = dict(cases)
        for key, value in self._cases.items():
            setattr(self, key, value)

    def __getitem__(self, key):
        return self._cases[key]

    def __setitem__(self, key, value):
        self._cases[key] = value
        setattr(self, key, value)


# ZMIANA: Zezwalamy na dostęp do bazy dla transaction.on_commit
pytestmark = [pytest.mark.integration, pytest.mark.django_db]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def factory(use_cases):
    from django.test import RequestFactory

    class SessionRequestFactory(RequestFactory):
        def generic(self, *args, **kwargs):
            req = super().generic(*args, **kwargs)
            req.session = {}
            req.app_container = use_cases
            return req

    return SessionRequestFactory()


@pytest.fixture
def mock_user():
    """Fake authenticated user — bez zapisu do bazy."""
    user = MagicMock()
    user.is_authenticated = True
    user.id = 1
    user.username = "turysta"

    # Zmockowanie zachowania konta rodzinnego: request.user.profiles.first().id
    mock_profile = MagicMock()
    mock_profile.id = 1
    user.profiles.first.return_value = mock_profile

    return user


@pytest.fixture
def use_cases():
    """Zwraca kontener mocków Use Case'ów.

    Views używają request.app_container (ustawianego przez ContainerMiddleware),
    a nie bezpośredniego importu get_container. Fixture factory automatycznie
    wstrzykuje ten kontener do każdego requestu.
    """
    cases = {
        "log_ascent": MagicMock(),
        "start_badge_progress": MagicMock(),
        "verify_badge": MagicMock(),
        "explore_map": MagicMock(),
        "advance_logistic_status": MagicMock(),
        "unsubscribe_badge": MagicMock(),
        "get_mvt_tile": MagicMock(),
        "evaluate_badge_progress": MagicMock(),
        "bulk_log_ascents": MagicMock(),
        "analyze_gpx_track": MagicMock(),
    }
    container = UseCaseContainer(cases)
    yield container


# ---------------------------------------------------------------------------
# AscentLogView — POST /api/v1/ascents/
# ---------------------------------------------------------------------------


class TestAscentLogView:
    """Testy endpointu logowania wędrówek."""

    def test_created_returns_201_with_ascent_id(self, factory, mock_user, use_cases) -> None:
        """Zwraca 201 z identyfikatorem wejścia po poprawnym zalogowaniu wędrówki."""
        from apps.api.views import AscentLogView

        use_cases["log_ascent"].execute.return_value = 77

        request = factory.post(
            "/api/v1/ascents/",
            data=json.dumps({"peak_id": 15, "ascent_date": TEST_TODAY}),
            content_type="application/json",
        )
        request.user = mock_user

        response = AscentLogView.as_view()(request)

        assert response.status_code == 201
        assert json.loads(response.content)["ascent_id"] == 77

    def test_profile_id_from_session_not_body(self, factory, mock_user, use_cases) -> None:
        """SECURITY: profile_id musi pochodzić z autoryzacji, a nie z payloadu."""
        from apps.api.views import AscentLogView

        use_cases["log_ascent"].execute.return_value = 1

        request = factory.post(
            "/api/v1/ascents/",
            data=json.dumps({"peak_id": 15, "ascent_date": TEST_TODAY, "profile_id": 999}),
            content_type="application/json",
        )
        request.user = mock_user

        AscentLogView.as_view()(request)

        call_kwargs = use_cases["log_ascent"].execute.call_args
        assert call_kwargs.kwargs["profile_id"] == 1

    def test_conflict_error_returns_409_rfc7807(self, factory, mock_user, use_cases) -> None:
        """Zwraca 409 w formacie RFC 7807 przy konflikcie duplikatu wejścia."""
        from application.exceptions import ConflictError
        from apps.api.views import AscentLogView

        use_cases["log_ascent"].execute.side_effect = ConflictError("Wejście jest duplikatem")

        request = factory.post(
            "/api/v1/ascents/",
            data=json.dumps({"peak_id": 15, "ascent_date": TEST_TODAY}),
            content_type="application/json",
        )
        request.user = mock_user

        response = AscentLogView.as_view()(request)

        assert response.status_code == 409
        data = json.loads(response.content)
        assert data["status"] == 409
        assert "Konflikt danych" in data["detail"]
        assert "request_id" in data

    def test_bitemporal_error_returns_422(self, factory, mock_user, use_cases) -> None:
        """Zwraca 422 przy nieprawidłowym czasie bitemporalnym."""
        from application.exceptions import BitemporalTimeError
        from apps.api.views import AscentLogView

        use_cases["log_ascent"].execute.side_effect = BitemporalTimeError("Błąd")

        request = factory.post(
            "/api/v1/ascents/",
            data=json.dumps({"peak_id": 15, "ascent_date": "1800-01-01"}),
            content_type="application/json",
        )
        request.user = mock_user

        response = AscentLogView.as_view()(request)

        assert response.status_code == 422
        data = json.loads(response.content)
        assert "request_id" in data


class TestBadgeSubscribeView:
    """Testy endpointu subskrypcji odznak."""

    def test_subscribe_returns_201_with_progress_id(self, factory, mock_user, use_cases) -> None:
        """Zwraca 201 z identyfikatorem postępu po subskrypcji odznaki."""
        from apps.api.views import BadgeSubscribeView

        use_cases["start_badge_progress"].execute.return_value = 99

        request = factory.post("/api/v1/badges/KGP/subscribe/")
        request.user = mock_user

        response = BadgeSubscribeView.as_view()(request, badge_code="KGP")

        assert response.status_code == 201
        assert json.loads(response.content)["progress_id"] == 99

    def test_subscribe_calls_use_case_with_correct_args(self, factory, mock_user, use_cases) -> None:
        """Wywołuje use case subskrypcji z poprawnymi argumentami."""
        from apps.api.views import BadgeSubscribeView

        use_cases["start_badge_progress"].execute.return_value = 1

        request = factory.post("/api/v1/badges/KGP/subscribe/")
        request.user = mock_user

        BadgeSubscribeView.as_view()(request, badge_code="KGP")

        use_cases["start_badge_progress"].execute.assert_called_once_with(profile_id=1, badge_code="KGP")


# ---------------------------------------------------------------------------
# BadgeProgressView — GET /api/v1/badges/{badge_code}/progress/
# ---------------------------------------------------------------------------


class TestBadgeProgressView:
    """Testy endpointu postępu odznaki."""

    def test_progress_200_returns_evaluation_result(self, factory, mock_user, use_cases) -> None:
        """Zwraca 200 z wynikiem ewaluacji postępu odznaki."""
        from application.dto.verify_badge_dto import VerifyBadgeResponseDTO
        from apps.api.views import BadgeProgressView

        use_cases["evaluate_badge_progress"].execute.return_value = VerifyBadgeResponseDTO(
            verified=False,
            status="IN_PROGRESS",
            errors=[],
            valid_ascents_count=12,
        )

        request = factory.get("/api/v1/badges/KGP/progress/")
        request.user = mock_user

        response = BadgeProgressView.as_view()(request, badge_code="KGP")

        assert response.status_code == 200
        assert json.loads(response.content)["valid_ascents_count"] == 12

    def test_not_subscribed_returns_404_rfc7807(self, factory, mock_user, use_cases) -> None:
        """Zwraca 404 gdy użytkownik nie jest subskrybentem odznaki."""
        from application.exceptions import ResourceNotFoundError
        from apps.api.views import BadgeProgressView

        use_cases["evaluate_badge_progress"].execute.side_effect = ResourceNotFoundError("Nie subskrybuje")

        request = factory.get("/api/v1/badges/KGP/progress/")
        request.user = mock_user

        response = BadgeProgressView.as_view()(request, badge_code="KGP")

        assert response.status_code == 404
        data = json.loads(response.content)
        assert data["status"] == 404
        assert "request_id" in data


# ---------------------------------------------------------------------------
# BadgeLogisticsView — PATCH /api/v1/progress/{progress_id}/logistics/
# ---------------------------------------------------------------------------


class TestBadgeLogisticsView:
    """Testy endpointu logistyki odznaki."""

    def test_patch_returns_200_on_success(self, factory, mock_user, use_cases) -> None:
        """Zwraca 200 po pomyślnej aktualizacji statusu logistycznego."""
        from apps.api.views import BadgeLogisticsView

        use_cases["advance_logistic_status"].execute.return_value = None

        request = factory.patch(
            "/api/v1/progress/1/logistics/",
            data=json.dumps({"logistic_status": "WAITING_FOR_VERIFICATION", "status_date": TEST_TODAY}),
            content_type="application/json",
        )
        request.user = mock_user

        response = BadgeLogisticsView.as_view()(request, progress_id=1)

        assert response.status_code == 200
        assert json.loads(response.content)["status"] == "UPDATED"

    def test_patch_conflict_returns_409(self, factory, mock_user, use_cases) -> None:
        """Zwraca 409 przy niedozwolonym przejściu statusu logistycznego (FSM Kanban)."""
        from application.exceptions import IllegalStateTransitionError
        from apps.api.views import BadgeLogisticsView

        use_cases["advance_logistic_status"].execute.side_effect = IllegalStateTransitionError("Niedozwolone przejście")

        request = factory.patch(
            "/api/v1/progress/1/logistics/",
            data=json.dumps({"logistic_status": "ALBUM", "status_date": TEST_TODAY}),
            content_type="application/json",
        )
        request.user = mock_user

        response = BadgeLogisticsView.as_view()(request, progress_id=1)

        assert response.status_code == 409
        data = json.loads(response.content)
        assert data["type"] == "https://api.pttk-badges.pl/errors/invalid-state-transition"
        assert "request_id" in data


# ---------------------------------------------------------------------------
# MapObjectsView — GET /api/v1/map/objects
# ---------------------------------------------------------------------------


class TestMapObjectsView:
    """Testy endpointu mapy obiektów turystycznych."""

    def test_returns_geojson_for_valid_bbox(self, factory, mock_user, use_cases) -> None:
        """Zwraca GeoJSON dla poprawnego bounding box."""
        from apps.api.views import MapObjectsView

        use_cases["explore_map"].execute.return_value = {"type": "FeatureCollection", "features": []}

        request = factory.get("/api/v1/map/objects/?bbox=10,20,30,40")
        request.user = mock_user

        response = MapObjectsView.as_view()(request)

        assert response.status_code == 200

    def test_returns_422_for_missing_bbox(self, factory, mock_user, use_cases) -> None:
        """Zwraca 422 gdy brakuje wymaganego parametru bbox."""
        from apps.api.views import MapObjectsView

        request = factory.get("/api/v1/map/objects/")
        request.user = mock_user

        response = MapObjectsView.as_view()(request)

        assert response.status_code == 422
        data = json.loads(response.content)
        assert "request_id" in data

    def test_returns_422_for_out_of_range_bbox(self, factory, mock_user, use_cases) -> None:
        """Zwraca 422 gdy bbox poza dozwolonym zakresem geograficznym (AUDYT-049).

        Chroni PostGIS i cache przed atakiem DoS poprzez fałszywy wektor
        (np. -999,-999,999,999) skanujący całą tabelę.
        """
        from apps.api.views import MapObjectsView

        request = factory.get("/api/v1/map/objects/?bbox=-999,-999,999,999")
        request.user = mock_user

        response = MapObjectsView.as_view()(request)

        assert response.status_code == 422
        data = json.loads(response.content)
        assert "request_id" in data


# ---------------------------------------------------------------------------
# VectorTileView — GET /api/v1/tiles/{layer}/{z}/{x}/{y}.pbf
# ---------------------------------------------------------------------------


class TestVectorTileView:
    """Testy endpointu kafelków wektorowych."""

    def test_returns_tile_data(self, factory, use_cases) -> None:
        """Zwraca dane kafelka wektorowego."""
        from apps.api.views import VectorTileView

        use_cases["get_mvt_tile"] = MagicMock()
        use_cases["get_mvt_tile"].execute.return_value = b"tile_data"

        request = factory.get("/api/v1/tiles/country/5/10/15.pbf")

        response = VectorTileView.as_view()(request, layer="country", z=5, x=10, y=15)

        assert response.status_code == 200

    def test_returns_204_for_empty_tile(self, factory, use_cases) -> None:
        """Zwraca 204 gdy kafelek wektorowy jest pusty."""
        from apps.api.views import VectorTileView

        use_cases["get_mvt_tile"] = MagicMock()
        use_cases["get_mvt_tile"].execute.return_value = None

        request = factory.get("/api/v1/tiles/country/5/10/15.pbf")

        response = VectorTileView.as_view()(request, layer="country", z=5, x=10, y=15)

        assert response.status_code == 204


# ---------------------------------------------------------------------------
# ProfileSettingsView — PATCH /api/v1/profiles/{profile_id}/
# ---------------------------------------------------------------------------


class TestProfileSettingsView:
    """Testy endpointu ustawień profilu."""

    def test_updates_profile_settings(self, factory, mock_user, use_cases) -> None:
        """Aktualizuje ustawienia profilu użytkownika."""
        from apps.api.views import ProfileSettingsView
        from apps.tourists.models import TouristProfile

        mock_profile = MagicMock(spec=TouristProfile)
        mock_profile.user = mock_user
        mock_profile.nickname = "old_nick"
        mock_profile.birth_date = None
        mock_profile.preferred_base_map = "osm"

        with patch("apps.api.views.get_object_or_404", return_value=mock_profile):
            request = factory.patch(
                "/api/v1/profiles/1/",
                data=json.dumps({"nickname": "new_nick", "preferred_base_map": "satellite"}),
                content_type="application/json",
            )
            request.user = mock_user

            response = ProfileSettingsView.as_view()(request, profile_id=1)

            assert response.status_code == 200
            mock_profile.save.assert_called_once()

    def test_clears_birth_date_on_empty_string(self, factory, mock_user, use_cases) -> None:
        """Czyści datę urodzenia przy pustym ciągu znaków — tylko gdy jeszcze nie była ustawiona."""
        from apps.api.views import ProfileSettingsView
        from apps.tourists.models import TouristProfile

        mock_profile = MagicMock(spec=TouristProfile)
        mock_profile.user = mock_user
        mock_profile.birth_date = None

        with patch("apps.api.views.get_object_or_404", return_value=mock_profile):
            request = factory.patch(
                "/api/v1/profiles/1/",
                data=json.dumps({"birth_date": ""}),
                content_type="application/json",
            )
            request.user = mock_user

            response = ProfileSettingsView.as_view()(request, profile_id=1)

            assert response.status_code == 200
            assert mock_profile.birth_date is None

    def test_rejects_birth_date_change_when_already_set(self, factory, mock_user, use_cases) -> None:
        """SECURITY: Odmusza zmiany birth_date gdy już ustawiona (AUDYT-048, Age Fraud)."""
        from datetime import date

        from apps.api.views import ProfileSettingsView
        from apps.tourists.models import TouristProfile

        mock_profile = MagicMock(spec=TouristProfile)
        mock_profile.user = mock_user
        mock_profile.birth_date = date(2000, 1, 1)

        with patch("apps.api.views.get_object_or_404", return_value=mock_profile):
            request = factory.patch(
                "/api/v1/profiles/1/",
                data=json.dumps({"birth_date": "1990-05-15"}),
                content_type="application/json",
            )
            request.user = mock_user

            response = ProfileSettingsView.as_view()(request, profile_id=1)

            assert response.status_code == 409
            data = json.loads(response.content)
            assert data["detail"] == "Data urodzenia nie może być zmieniona po ustawieniu."
            assert "request_id" in data

    def test_rejects_birth_date_clear_when_already_set(self, factory, mock_user, use_cases) -> None:
        """SECURITY: Odmusza wyczyszczenia birth_date gdy już ustawiona (AUDYT-048)."""
        from datetime import date

        from apps.api.views import ProfileSettingsView
        from apps.tourists.models import TouristProfile

        mock_profile = MagicMock(spec=TouristProfile)
        mock_profile.user = mock_user
        mock_profile.birth_date = date(2000, 1, 1)

        with patch("apps.api.views.get_object_or_404", return_value=mock_profile):
            request = factory.patch(
                "/api/v1/profiles/1/",
                data=json.dumps({"birth_date": ""}),
                content_type="application/json",
            )
            request.user = mock_user

            response = ProfileSettingsView.as_view()(request, profile_id=1)

            assert response.status_code == 409
            data = json.loads(response.content)
            assert "request_id" in data


# ---------------------------------------------------------------------------
# BadgeSubscribeView — DELETE /api/v1/badges/{badge_code}/subscribe/
# ---------------------------------------------------------------------------


class TestBadgeUnsubscribeView:
    """Testy endpointu wypisywania z odznak."""

    def test_unsubscribe_returns_200(self, factory, mock_user, use_cases) -> None:
        """Zwraca 200 po pomyślnym wypisaniu z odznaki."""
        from apps.api.views import BadgeSubscribeView

        use_cases["unsubscribe_badge"] = MagicMock()

        request = factory.delete("/api/v1/badges/KGP/subscribe/")
        request.user = mock_user

        response = BadgeSubscribeView.as_view()(request, badge_code="KGP")

        assert response.status_code == 200
        use_cases["unsubscribe_badge"].execute.assert_called_once_with(profile_id=1, badge_code="KGP")

    def test_unsubscribe_handles_conflict_error(self, factory, mock_user, use_cases) -> None:
        """Obsługuje konflikt podczas wypisywania z odznaki."""
        from application.exceptions import ConflictError
        from apps.api.views import BadgeSubscribeView

        use_cases["unsubscribe_badge"] = MagicMock()
        use_cases["unsubscribe_badge"].execute.side_effect = ConflictError("Cannot unsubscribe")

        request = factory.delete("/api/v1/badges/KGP/subscribe/")
        request.user = mock_user

        response = BadgeSubscribeView.as_view()(request, badge_code="KGP")

        assert response.status_code == 409
        data = json.loads(response.content)
        assert "request_id" in data


# ---------------------------------------------------------------------------
# GpxAnalyzeView — POST /api/v1/gpx/analyze/
# ---------------------------------------------------------------------------


class TestGpxAnalyzeView:
    """Testy endpointu analizy plików GPX."""

    def test_requires_authentication(self, factory, use_cases) -> None:
        """Wymaga autoryzacji użytkownika."""
        from apps.api.views import GpxAnalyzeView

        request = factory.post("/api/v1/gpx/analyze/")
        request.user = MagicMock()
        request.user.is_authenticated = False

        response = GpxAnalyzeView.as_view()(request)

        assert response.status_code == 401
        data = json.loads(response.content)
        assert "request_id" in data

    def test_returns_422_when_no_file(self, factory, mock_user, use_cases) -> None:
        """Zwraca 422 gdy nie przesłano pliku GPX."""
        from apps.api.views import GpxAnalyzeView

        request = factory.post("/api/v1/gpx/analyze/")
        request.user = mock_user

        response = GpxAnalyzeView.as_view()(request)

        assert response.status_code == 422
        data = json.loads(response.content)
        assert "request_id" in data

    def test_returns_422_when_file_too_large(self, factory, mock_user, use_cases) -> None:
        """Zwraca 422 gdy plik GPX przekracza limit rozmiaru."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.api.views import GpxAnalyzeView

        large_content = b"x" * (11 * 1024 * 1024)
        mock_file = SimpleUploadedFile("test.gpx", large_content, content_type="application/gpx+xml")

        request = factory.post(
            "/api/v1/gpx/analyze/",
            data={"file": mock_file},
            format="multipart",
        )
        request.user = mock_user
        request.session["active_profile_id"] = 1

        response = GpxAnalyzeView.as_view()(request)

        assert response.status_code == 422
        data = json.loads(response.content)
        assert data["detail"] == "Plik GPX nie może przekraczać 10 MB."
        assert "request_id" in data

    def test_returns_422_when_invalid_mime_type(self, factory, mock_user, use_cases) -> None:
        """SECURITY: Odrzuca pliki o niebezpiecznym Content-Type (AUDYT-050)."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.api.views import GpxAnalyzeView

        fake_file = SimpleUploadedFile("malware.exe", b"MZ\x90\x00", content_type="application/x-msdownload")

        request = factory.post(
            "/api/v1/gpx/analyze/",
            data={"file": fake_file},
            format="multipart",
        )
        request.user = mock_user
        request.session["active_profile_id"] = 1

        response = GpxAnalyzeView.as_view()(request)

        assert response.status_code == 422
        data = json.loads(response.content)
        assert data["detail"] == "Akceptowane są pliki GPX (application/gpx+xml, text/xml)."
        assert "request_id" in data

    def test_returns_422_when_file_not_xml(self, factory, mock_user, use_cases) -> None:
        """SECURITY: Odrzuca plik oznaczony jako XML, ale bez magic bytes XML/GPX."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.api.views import GpxAnalyzeView

        fake_file = SimpleUploadedFile("not_gpx.xml", b"NOT XML CONTENT AT ALL", content_type="text/xml")

        request = factory.post(
            "/api/v1/gpx/analyze/",
            data={"file": fake_file},
            format="multipart",
        )
        request.user = mock_user
        request.session["active_profile_id"] = 1

        response = GpxAnalyzeView.as_view()(request)

        assert response.status_code == 422
        data = json.loads(response.content)
        assert data["detail"] == "Plik nie jest prawidłowym plikiem GPX ani XML."
        assert "request_id" in data


# ---------------------------------------------------------------------------
# BulkAscentLogView — POST /api/v1/ascents/bulk/
# ---------------------------------------------------------------------------


class TestBulkAscentLogView:
    """Testy endpointu masowego logowania wędrówek."""

    def test_requires_authentication(self, factory, use_cases) -> None:
        """Wymaga autoryzacji użytkownika."""
        from apps.api.views import BulkAscentLogView

        request = factory.post("/api/v1/ascents/bulk/")
        request.user = MagicMock()
        request.user.is_authenticated = False

        response = BulkAscentLogView.as_view()(request)

        assert response.status_code == 401
        data = json.loads(response.content)
        assert "request_id" in data

    def test_returns_422_for_invalid_json(self, factory, mock_user, use_cases) -> None:
        """Zwraca 422 przy nieprawidłowym JSON w żądaniu."""
        from apps.api.views import BulkAscentLogView

        request = factory.post("/api/v1/ascents/bulk/", data="not json", content_type="application/json")
        request.user = mock_user

        response = BulkAscentLogView.as_view()(request)

        assert response.status_code == 422
        data = json.loads(response.content)
        assert "request_id" in data

    def test_returns_422_for_non_list_body(self, factory, mock_user, use_cases) -> None:
        """Zwraca 422 gdy ciało żądania nie jest listą."""
        from apps.api.views import BulkAscentLogView

        request = factory.post(
            "/api/v1/ascents/bulk/", data=json.dumps({"not": "a list"}), content_type="application/json"
        )
        request.user = mock_user

        response = BulkAscentLogView.as_view()(request)

        assert response.status_code == 422
        data = json.loads(response.content)
        assert "request_id" in data


# ---------------------------------------------------------------------------
# ProfileUpgradeView — POST /api/v1/profiles/{profile_id}/upgrade/
# ---------------------------------------------------------------------------


class TestProfileUpgradeView:
    """Testy endpointu podwyższenia profilu do PRO."""

    def test_requires_authentication(self, factory, use_cases) -> None:
        """Wymaga autoryzacji użytkownika."""
        from apps.api.views import ProfileUpgradeView

        request = factory.post("/api/v1/profiles/1/upgrade/")
        request.user = MagicMock()
        request.user.is_authenticated = False

        response = ProfileUpgradeView.as_view()(request, profile_id=1)

        assert response.status_code == 401
        data = json.loads(response.content)
        assert "request_id" in data

    def test_upgrades_profile_to_pro(self, factory, mock_user, use_cases) -> None:
        """Podwyższa profil użytkownika do planu PRO."""
        from apps.api.views import ProfileUpgradeView
        from apps.tourists.models import TouristProfile

        mock_profile = MagicMock(spec=TouristProfile)
        mock_profile.user = mock_user
        mock_profile.active_plan = "FREE"

        with patch("apps.api.views.get_object_or_404", return_value=mock_profile):
            request = factory.post("/api/v1/profiles/1/upgrade/")
            request.user = mock_user

            response = ProfileUpgradeView.as_view()(request, profile_id=1)

            assert response.status_code == 200
            assert mock_profile.active_plan == "PRO"
            mock_profile.save.assert_called_once()

    def test_returns_404_when_profile_not_found(self, factory, mock_user, use_cases) -> None:
        """Zwraca 404 gdy profil nie istnieje."""
        from django.http import Http404

        from apps.api.views import ProfileUpgradeView

        with patch("apps.api.views.get_object_or_404", side_effect=Http404):
            request = factory.post("/api/v1/profiles/1/upgrade/")
            request.user = mock_user

            response = ProfileUpgradeView.as_view()(request, profile_id=1)

            assert response.status_code == 404
            data = json.loads(response.content)
            assert "request_id" in data


# ---------------------------------------------------------------------------
# Additional error handling tests
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Testy obsługi błędów API."""

    def test_vector_tile_handles_application_exception(self, factory, use_cases) -> None:
        """Obsługuje ApplicationException w widoku kafelków wektorowych."""
        from application.exceptions import UseCaseError
        from apps.api.views import VectorTileView

        use_cases["get_mvt_tile"] = MagicMock()
        use_cases["get_mvt_tile"].execute.side_effect = UseCaseError("Invalid layer")

        request = factory.get("/api/v1/tiles/country/5/10/15.pbf")

        response = VectorTileView.as_view()(request, layer="country", z=5, x=10, y=15)

        assert response.status_code == 422
        data = json.loads(response.content)
        assert "request_id" in data

    def test_map_objects_handles_invalid_bbox_format(self, factory, mock_user, use_cases) -> None:
        """Obsługuje nieprawidłowy format parametru bbox."""
        from apps.api.views import MapObjectsView

        request = factory.get("/api/v1/map/objects/?bbox=invalid,format")
        request.user = mock_user

        response = MapObjectsView.as_view()(request)

        assert response.status_code == 422
        data = json.loads(response.content)
        assert "request_id" in data

    def test_map_objects_passes_optional_params(self, factory, mock_user, use_cases) -> None:
        """Przekazuje opcjonalne parametry do use case explore_map."""
        from apps.api.views import MapObjectsView

        use_cases["explore_map"].execute.return_value = {"type": "FeatureCollection", "features": []}

        request = factory.get(
            "/api/v1/map/objects/?bbox=10,20,30,40&badge_code=KGP&region_level=voivodeship&region_id=5"
        )
        request.user = mock_user

        response = MapObjectsView.as_view()(request)

        assert response.status_code == 200
        use_cases["explore_map"].execute.assert_called_once()
        call_args = use_cases["explore_map"].execute.call_args
        assert call_args.args[0].badge_code == "KGP"
        assert call_args.args[0].region_level == "voivodeship"
        assert call_args.args[0].region_id == 5

    def test_map_objects_handles_dto_validation_error(self, factory, mock_user, use_cases) -> None:
        """Obsługuje błąd walidacji DTO dla mapy obiektów."""
        from apps.api.views import MapObjectsView

        request = factory.get("/api/v1/map/objects/?bbox=10,20,30,40&region_id=invalid")
        request.user = mock_user

        response = MapObjectsView.as_view()(request)

        assert response.status_code == 422
        data = json.loads(response.content)
        assert "request_id" in data

    def test_map_objects_requires_authentication(self, factory, use_cases) -> None:
        """Zwraca 401 gdy użytkownik nie jest zalogowany."""
        from apps.api.views import MapObjectsView

        request = factory.get("/api/v1/map/objects/?bbox=10,20,30,40")
        request.user = MagicMock()
        request.user.is_authenticated = False

        response = MapObjectsView.as_view()(request)

        assert response.status_code == 401
        data = json.loads(response.content)
        assert "request_id" in data


# ---------------------------------------------------------------------------
# NearbyObjectsView — GET /api/v1/objects/{id}/nearby/
# ---------------------------------------------------------------------------


class TestNearbyObjectsView:
    """Testy endpointu nearby obiektów turystycznych."""

    def test_returns_empty_features_when_no_geom(self, factory, use_cases) -> None:
        """Zwraca pustą listę obiektów gdy brak geometrii."""
        from apps.api.views import NearbyObjectsView
        from apps.badges.models import TouristObject

        mock_obj = MagicMock(spec=TouristObject)
        mock_obj.geom = None

        with patch("apps.api.views.get_object_or_404", return_value=mock_obj):
            request = factory.get("/api/v1/objects/1/nearby/")

            response = NearbyObjectsView.as_view()(request, object_id=1)

            assert response.status_code == 200
            data = json.loads(response.content)
            assert data["type"] == "FeatureCollection"
            assert data["features"] == []

    def test_returns_features_with_colors_for_authenticated_user(self, factory, use_cases) -> None:
        """Zwraca obiekty z kolorami dla zalogowanego użytkownika."""
        from django.contrib.gis.geos import Point

        from apps.api.views import NearbyObjectsView
        from apps.badges.models import TouristObject

        mock_obj = MagicMock(spec=TouristObject)
        mock_obj.geom = Point(10, 20)
        mock_obj.id = 1
        mock_obj.name = "Test Peak"
        mock_obj.type = "peak"

        with patch("apps.api.views.get_object_or_404", return_value=mock_obj):
            with patch("apps.badges.models.TouristObject.objects.filter") as mock_filter:
                mock_filter.return_value.exclude.return_value.__getitem__.return_value = []

                request = factory.get("/api/v1/objects/1/nearby/")
                request.user = MagicMock()
                request.user.is_authenticated = True
                request.user.id = 1

                response = NearbyObjectsView.as_view()(request, object_id=1)

                assert response.status_code == 200
                data = json.loads(response.content)
                assert len(data["features"]) == 1
                assert data["features"][0]["properties"]["is_center"] is True


# ---------------------------------------------------------------------------
# ProfileSettingsView additional tests
# ---------------------------------------------------------------------------


class TestProfileSettingsViewAdditional:
    """Dodatkowe testy ustawień profilu."""

    def test_returns_404_when_profile_not_owned(self, factory, mock_user, use_cases) -> None:
        """Zwraca 404 gdy profil nie należy do użytkownika."""
        from django.http import Http404

        from apps.api.views import ProfileSettingsView

        with patch("apps.api.views.get_object_or_404", side_effect=Http404):
            request = factory.patch(
                "/api/v1/profiles/999/",
                data=json.dumps({"nickname": "hacker"}),
                content_type="application/json",
            )
            request.user = mock_user

            response = ProfileSettingsView.as_view()(request, profile_id=999)

            assert response.status_code == 404
            data = json.loads(response.content)
            assert "request_id" in data

    def test_handles_validation_error(self, factory, mock_user, use_cases) -> None:
        """Obsługuje błąd walidacji danych profilu."""
        from apps.api.views import ProfileSettingsView
        from apps.tourists.models import TouristProfile

        mock_profile = MagicMock(spec=TouristProfile)
        mock_profile.user = mock_user

        with patch("apps.api.views.get_object_or_404", return_value=mock_profile):
            request = factory.patch(
                "/api/v1/profiles/1/",
                data=json.dumps({"birth_date": "invalid-date"}),
                content_type="application/json",
            )
            request.user = mock_user

            response = ProfileSettingsView.as_view()(request, profile_id=1)

        assert response.status_code == 422
        data = json.loads(response.content)
        assert "request_id" in data


# ---------------------------------------------------------------------------
# BadgeProgressView additional tests
# ---------------------------------------------------------------------------


class TestBadgeProgressViewAdditional:
    """Dodatkowe testy postępu odznaki."""

    def test_handles_dto_validation_error(self, factory, mock_user, use_cases) -> None:
        """Obsługuje błąd walidacji DTO."""
        from apps.api.views import BadgeProgressView

        request = factory.get("/api/v1/badges/KGP/progress/?cycle=invalid")
        request.user = mock_user

        response = BadgeProgressView.as_view()(request, badge_code="KGP")

        assert response.status_code == 422
        data = json.loads(response.content)
        assert "request_id" in data

    def test_requires_authentication(self, factory, use_cases) -> None:
        """Wymaga autoryzacji użytkownika."""
        from apps.api.views import BadgeProgressView

        request = factory.get("/api/v1/badges/KGP/progress/")
        request.user = MagicMock()
        request.user.is_authenticated = False

        response = BadgeProgressView.as_view()(request, badge_code="KGP")

        assert response.status_code == 401
        data = json.loads(response.content)
        assert "request_id" in data


# ---------------------------------------------------------------------------
# BadgeLogisticsView additional tests
# ---------------------------------------------------------------------------


class TestBadgeLogisticsViewAdditional:
    """Dodatkowe testy logistyki odznaki."""

    def test_requires_authentication(self, factory, use_cases) -> None:
        """Wymaga autoryzacji użytkownika."""
        from apps.api.views import BadgeLogisticsView

        request = factory.patch(
            "/api/v1/progress/1/logistics/",
            data=json.dumps({"logistic_status": "ALBUM", "status_date": TEST_TODAY}),
            content_type="application/json",
        )
        request.user = MagicMock()
        request.user.is_authenticated = False

        response = BadgeLogisticsView.as_view()(request, progress_id=1)

        assert response.status_code == 401
        data = json.loads(response.content)
        assert "request_id" in data

    def test_handles_invalid_json(self, factory, mock_user, use_cases) -> None:
        """Obsługuje nieprawidłowy JSON w żądaniu."""
        from apps.api.views import BadgeLogisticsView

        request = factory.patch(
            "/api/v1/progress/1/logistics/",
            data="not json",
            content_type="application/json",
        )
        request.user = mock_user

        response = BadgeLogisticsView.as_view()(request, progress_id=1)

        assert response.status_code == 422
        data = json.loads(response.content)
        assert "request_id" in data

    def test_handles_dto_validation_error(self, factory, mock_user, use_cases) -> None:
        """Obsługuje błąd walidacji DTO."""
        from apps.api.views import BadgeLogisticsView

        request = factory.patch(
            "/api/v1/progress/1/logistics/",
            data=json.dumps({"invalid": "data"}),
            content_type="application/json",
        )
        request.user = mock_user

        response = BadgeLogisticsView.as_view()(request, progress_id=1)

        assert response.status_code == 422
        data = json.loads(response.content)
        assert "request_id" in data

    def test_returns_404_when_progress_not_owned(self, factory, mock_user, use_cases) -> None:
        """Zwraca 404 gdy postęp odznaki nie należy do profilu."""
        from application.exceptions import ResourceNotFoundError
        from apps.api.views import BadgeLogisticsView

        use_cases["advance_logistic_status"].execute.side_effect = ResourceNotFoundError(
            "Progress nie należy do tego profilu."
        )

        request = factory.patch(
            "/api/v1/progress/999/logistics/",
            data=json.dumps({"logistic_status": "ALBUM", "status_date": TEST_TODAY}),
            content_type="application/json",
        )
        request.user = mock_user

        response = BadgeLogisticsView.as_view()(request, progress_id=999)

        assert response.status_code == 404
        data = json.loads(response.content)
        assert "request_id" in data


# ---------------------------------------------------------------------------
# AscentLogView additional tests
# ---------------------------------------------------------------------------


class TestAscentLogViewAdditional:
    """Dodatkowe testy logowania wędrówek."""

    def test_handles_dto_validation_error(self, factory, mock_user, use_cases) -> None:
        """Obsługuje błąd walidacji DTO."""
        from apps.api.views import AscentLogView

        request = factory.post(
            "/api/v1/ascents/",
            data=json.dumps({"peak_id": 15, "ascent_date": "invalid-date"}),
            content_type="application/json",
        )
        request.user = mock_user

        response = AscentLogView.as_view()(request)

        assert response.status_code == 422
        data = json.loads(response.content)
        assert "request_id" in data

    def test_handles_missing_peak_id(self, factory, mock_user, use_cases) -> None:
        """Obsługuje brak wymaganego parametru peak_id."""
        from apps.api.views import AscentLogView

        request = factory.post(
            "/api/v1/ascents/",
            data=json.dumps({"ascent_date": TEST_TODAY}),
            content_type="application/json",
        )
        request.user = mock_user

        response = AscentLogView.as_view()(request)

        assert response.status_code == 422
        data = json.loads(response.content)
        assert "request_id" in data


# ---------------------------------------------------------------------------
# BadgeSubscribeView additional tests
# ---------------------------------------------------------------------------


class TestBadgeSubscribeViewAdditional:
    """Dodatkowe testy subskrypcji odznak."""

    def test_requires_authentication(self, factory, use_cases) -> None:
        """Wymaga autoryzacji użytkownika."""
        from apps.api.views import BadgeSubscribeView

        request = factory.post("/api/v1/badges/KGP/subscribe/")
        request.user = MagicMock()
        request.user.is_authenticated = False

        response = BadgeSubscribeView.as_view()(request, badge_code="KGP")

        assert response.status_code == 401
        data = json.loads(response.content)
        assert "request_id" in data

    def test_handles_use_case_error(self, factory, mock_user, use_cases) -> None:
        """Obsługuje błąd use case podczas subskrypcji odznaki."""
        from application.exceptions import UseCaseError
        from apps.api.views import BadgeSubscribeView

        use_cases["start_badge_progress"].execute.side_effect = UseCaseError("Test error")

        request = factory.post("/api/v1/badges/KGP/subscribe/")
        request.user = mock_user

        response = BadgeSubscribeView.as_view()(request, badge_code="KGP")

        assert response.status_code == 422
        data = json.loads(response.content)
        assert "request_id" in data


# ---------------------------------------------------------------------------
# VectorTileView additional tests
# ---------------------------------------------------------------------------


class TestVectorTileViewAdditional:
    """Dodatkowe testy kafelków wektorowych."""

    def test_returns_204_when_no_tile_data(self, factory, use_cases) -> None:
        """Zwraca 204 gdy brak danych kafelka."""
        from apps.api.views import VectorTileView

        use_cases["get_mvt_tile"] = MagicMock()
        use_cases["get_mvt_tile"].execute.return_value = None

        request = factory.get("/api/v1/tiles/country/5/10/15.pbf")

        response = VectorTileView.as_view()(request, layer="country", z=5, x=10, y=15)

        assert response.status_code == 204

    def test_sets_cache_headers(self, factory, use_cases) -> None:
        """Ustawia nagłówki cache dla kafelków wektorowych."""
        from apps.api.views import VectorTileView

        use_cases["get_mvt_tile"] = MagicMock()
        use_cases["get_mvt_tile"].execute.return_value = b"tile_data"

        request = factory.get("/api/v1/tiles/country/5/10/15.pbf")

        response = VectorTileView.as_view()(request, layer="country", z=5, x=10, y=15)

        assert response.status_code == 200
        assert response["Content-Encoding"] == "gzip"
        assert response["Cache-Control"] == "public, max-age=86400"


# ---------------------------------------------------------------------------
# BulkAscentLogView additional tests
# ---------------------------------------------------------------------------


class TestBulkAscentLogViewAdditional:
    """Dodatkowe testy masowego logowania wędrówek."""

    def test_handles_dto_validation_error(self, factory, mock_user, use_cases) -> None:
        """Obsługuje błąd walidacji DTO."""
        from apps.api.views import BulkAscentLogView

        request = factory.post(
            "/api/v1/ascents/bulk/",
            data=json.dumps([{"invalid": "data"}]),
            content_type="application/json",
        )
        request.user = mock_user

        response = BulkAscentLogView.as_view()(request)

        assert response.status_code == 422
        data = json.loads(response.content)
        assert "request_id" in data

    def test_skips_cache_when_no_ascents_saved(self, factory, mock_user, use_cases) -> None:
        """Pomija cache gdy nie zapisano żadnych wejść wędrówek."""
        from apps.api.views import BulkAscentLogView

        use_cases["bulk_log_ascents"] = MagicMock()
        use_cases["bulk_log_ascents"].execute.return_value = {"saved_count": 0}

        request = factory.post(
            "/api/v1/ascents/bulk/",
            data=json.dumps([]),
            content_type="application/json",
        )
        request.user = mock_user

        response = BulkAscentLogView.as_view()(request)

        assert response.status_code == 200
