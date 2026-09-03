"""Usługa Domenowa: Ochrona Praw Nabytów (Grandfather Clause).

AUDYT-016: Logika decyzyjna o tym, czy turysta zachowuje przyznaną odznakę
na stałe — została wydzielona z Orkiestratora (`VerifyBadgeUseCase`) do Czystej
Dziedziny.

AUDYT-132: Logika "Praw Nabytów" hermetyzowana w jednej usłudze —
`StartBadgeProgressUseCase` używa `determine_anchor_date()` zamiast
samodzielnie dobierać najstarsze wejście.

Zgodnie z TD-02: Czysta Domena chroni wszystkie niezmienniki biznesowe.
Use Case nie powinien "wiedzieć", czym jest prawo nabyte.
"""

from datetime import date

from domain.value_objects.verification_result import VerificationResult


class BadgeAwardingDomainService:
    """Serwis Domenowy decydujący o przyznaniu odznaki na stałe.

    Implementuje *Grandfather Clause*: jeżeli turysta już ma odznakę w stanie
    ``COMPLETED``, nowa weryfikacja nie może jej stracić — niezależnie od tego,
    co nowe reguły algorytmu powiedziały.

    Serwis jest **czysty** — nie zna repozytoriów ani infrastruktury.
    Przyjmuje gotowy wynik weryfikacji i status z bazy, zwraca ostateczną
    decyzję.
    """

    def __init__(self) -> None:
        """Serwis nie wymaga stanu — konstruktor pusty dla przejrzystości DI."""

    def resolve_final_status(
        self,
        persisted_status: str | None,
        domain_result: VerificationResult,
    ) -> tuple[str, bool]:
        """Rozdziela status końcowy i flagę weryfikacji.

        Args:
            persisted_status: Status zapisany w bazie danych (``COMPLETED``
                oznacza, że odznaka była już przyznana na stałe).
            domain_result: Wynik czystej weryfikacji matematycznej.

        Returns:
            Para: (status, verified). Gdy ``persisted_status == "COMPLETED"``
            zawsze zwraca ``("COMPLETED", True)`` — prawo nabytych chroni
            turystę przed utratą odznaki.
        """
        if persisted_status == "COMPLETED":
            return "COMPLETED", True
        return domain_result.status, domain_result.verified

    def determine_anchor_date(
        self,
        oldest_ascent_date: date | None,
        fallback_date: date,
    ) -> date:
        """Wyznacza datę zakotwiczenia wersji regulaminu (Grandfather Clause).

        Zasada Praw Nabytów: gdy turysta już miał wejścia na szczyty,
        najstarsze wejście staje się "datą zakotwiczenia" — odznaka jest
        wiązana z regulaminem obowiązującym właśnie wtedy, a nie z aktualną
        wersją. Gdy brak wejść, używana jest data bieżąca (fallback).

        Args:
            oldest_ascent_date: Data najstarszego istniejącego wejścia
                turysty dla danej odznaki (może być ``None`` gdy turysta
                nie ma żadnych wejść).
            fallback_date: Data domyślna (zazwyczaj ``clock.now().date()``),
                używana gdy nie ma żadnych wejść do zakotwiczenia.

        Returns:
            Data, dla której należy wybrać wersję regulaminu.
        """
        return oldest_ascent_date if oldest_ascent_date is not None else fallback_date
