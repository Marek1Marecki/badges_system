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

from domain.entities.badge_version import BadgeVersionDomain


class FakeBadgeRepository:
    """In-memory implementacja BadgeRepositoryPort.

    Przechowuje obiekty BadgeVersionDomain w słowniku indeksowanym
    krotką (badge_code, version_code) — identycznie jak klucz w metodzie
    get_badge_version() portu.
    """

    def __init__(self) -> None:
        """Inicjalizuje puste repozytorium."""
        self._store: dict[tuple[str, str], BadgeVersionDomain] = {}

    def add(
        self,
        badge_version: BadgeVersionDomain,
        *,
        code: str = "TEST",
        version: str = "2024",
    ) -> None:
        """Dodaje wersję odznaki do repozytorium.

        Args:
            badge_version: Obiekt domenowy do przechowania.
            code: Kod odznaki (klucz wyszukiwania). Domyślnie "TEST".
            version: Kod wersji (klucz wyszukiwania). Domyślnie "2024".
        """
        self._store[(code, version)] = badge_version

    def get_badge_version(self, badge_code: str, version_code: str) -> BadgeVersionDomain | None:
        """Zwraca wersję odznaki lub None jeśli nie istnieje.

        Implementuje BadgeRepositoryPort — identyczna sygnatura co adapter Django.

        Args:
            badge_code: Kod odznaki (np. "KGP").
            version_code: Kod wersji (np. "2024").

        Returns:
            BadgeVersionDomain lub None.
        """
        return self._store.get((badge_code, version_code))

    def clear(self) -> None:
        """Czyści wszystkie wpisy — przydatne między testami."""
        self._store.clear()

    def __len__(self) -> int:
        """Zwraca liczbę przechowywanych wersji odznak."""
        return len(self._store)
