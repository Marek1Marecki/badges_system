"""FakeBadgeRepository — in-memory implementacja BadgeRepositoryPort do testów.

Zgodnie z 17-determinism-contract.md i TEST_STRATEGY.md:
- Zero zależności od bazy danych
- Pełna kontrola nad zwracanymi danymi w testach
- Implementuje ten sam interfejs co DjangoBadgeRepository

Użycie:
    repo = FakeBadgeRepository()
    repo.add(badge_version)                        # dodaj wersję odznaki
    repo.add(badge_version, code="KGP", version="2024")  # z jawnym kluczem

    use_case = VerifyBadgeUseCase(repository=repo)
    result = use_case.execute(request_dto)
"""

from domain.entities.badge_version import BadgeTierDomain, BadgeVersionDomain


class FakeBadgeRepository:
    """In-memory implementacja BadgeRepositoryPort.

    Przechowuje obiekty BadgeVersionDomain w słowniku indeksowanym
    krotką (badge_code, version_code) — identycznie jak klucz w metodzie
    get_badge_version() portu.
    """

    def __init__(self) -> None:
        """Inicjalizuje puste repozytorium."""
        self._badges: dict[tuple[str, str], BadgeVersionDomain] = {}
        self._badges_by_id: dict[int, BadgeVersionDomain] = {}
        self._next_id = 1

    def add(self, *, code: str, version: str, badge: BadgeVersionDomain | None = None) -> None:
        """Dodaje wersję odznaki do repozytorium.

        Args:
            badge_version: Obiekt domenowy do przechowania.
            code: Kod odznaki (klucz wyszukiwania). Domyślnie "TEST".
            version: Kod wersji (klucz wyszukiwania). Domyślnie "2024".
        """
        # Automatyczne nadanie ID dla fake'owej wersji
        version_id = self._next_id
        self._next_id += 1

        if badge is None:
            # Domyślna, pusta odznaka jednostopniowa jeśli test nie przekazał własnej
            badge = BadgeVersionDomain(
                version_id=version_id,
                rules=[],
                pool_peak_ids=frozenset(),
                tiers=[BadgeTierDomain(tier_id=1, name="Standard", required_count=1, order=1)],
            )

        self._badges[(code, version)] = badge
        # Upewniamy się, że fake obsługuje wyszukiwanie po ID niezależnie od tego,
        # czy test podał własnego int'a czy stringa w version_id.
        if isinstance(badge.version_id, int):
            self._badges_by_id[badge.version_id] = badge
        else:
            self._badges_by_id[version_id] = badge

    def get_badge_version(self, badge_code: str, version_code: str) -> BadgeVersionDomain | None:
        """Zwraca wersję odznaki lub None jeśli nie istnieje.

        Implementuje BadgeRepositoryPort — identyczna sygnatura co adapter Django.

        Args:
            badge_code: Kod odznaki (np. "KGP").
            version_code: Kod wersji (np. "2024").

        Returns:
            BadgeVersionDomain lub None.
        """
        return self._badges.get((badge_code, version_code))

    def get_badge_version_by_id(self, version_id: int) -> BadgeVersionDomain | None:
        return self._badges_by_id.get(version_id)

    def get_version_id_for_date(self, badge_code: str, target_date: date) -> int | None:
        # Bardzo uproszczona logika na potrzeby testów Fake
        # Szuka pierwszej lepszej wersji pasującej do kodu odznaki
        for (code, _), badge in self._badges.items():
            if code == badge_code:
                return int(badge.version_id) if isinstance(badge.version_id, int) else 1
        return None

    def clear(self) -> None:
        """Czyści wszystkie wpisy — przydatne między testami."""
        self._badges.clear()
        self._badges_by_id.clear()
        self._next_id = 1

    def __len__(self) -> int:
        """Zwraca liczbę przechowywanych wersji odznak."""
        return len(self._badges)
