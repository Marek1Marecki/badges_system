"""Usługa Domenowa: Wycena szczytów i symulacja wejść (Domain Service).

AUDYT-035: Logika biznesowa — "Co jeżeli turysta wejdzie tu dzisiaj?" oraz
algebra punktowa `100 / missing` — została wydzielona z serwisu aplikacji
`PoiScoringService` do Czystej Dziedziny.

Serwis ten jest **czysty** — nie zna repozytoriów, cache ani zegara.
Przyjmuje gotowy agregat `BadgeVersionDomain` oraz jego wejścia i zwraca
wynik symulacji. Odpowiedzialność warstwy aplikacji (pobieranie danych,
buforowanie) leży po innym stronie interfejsu.
"""

from dataclasses import dataclass
from datetime import date

from domain.entities.badge_version import BadgeVersionDomain
from domain.value_objects.ascent import Ascent
from domain.value_objects.verification_context import VerificationContext

# Hierarchia kolorów zgodnie z ADR-010 i UI_GUIDELINES.md.
# Stosowany do priorytetyzacji wizualnej szczytów na mapie.
COLOR_PRIORITY: dict[str, int] = {
    "RED": 5,
    "ORANGE": 4,
    "GREEN": 3,
    "BLUE": 2,
    "GRAY": 1,
}


@dataclass(frozen=True)
class PeakSimulationResult:
    """Wynik symulacji dla jednego szczytu.

    - ``color``: aktualny kolor (GRY/ORANGE/GREEN/BLUE/RED)
    - ``score``: liczba punktów przyznana szczytu (0 dla nie-RED)
    """

    color: str
    score: int


class BadgeEligibilityDomainService:
    """Serwis Domenowy oceny wartości szczytów w puli odznaki.

    Enkapsuluje "magie wizualizacji" — algorytm symulacji wejść i algebrę
    punktową — tak by warstwa aplikacji mogła pozostać cienką warstwą
    orkiestrującą (pobieranie danych, TTL cache, publikacja zdarzeń).
    """

    def __init__(self) -> None:
        """Serwis nie wymaga stanu — konstruktor pusty dla przejrzystości DI."""

    def simulate_peak_value(
        self,
        version: BadgeVersionDomain,
        domain_ascents: list[Ascent],
        peak_id: int,
        today_date: date,
        current_cycle_peak_ids: frozenset[int],
        all_climbed_peak_ids: frozenset[int],
        context: VerificationContext,
        current_valid_count: int,
    ) -> PeakSimulationResult:
        """Oblicza wizualny wynik (kolor + score) dla jednego szczytu.

        Logika biznesowa:
        - GREEN: szczyt już zaliczony **w obecnym cyklu** (`current_cycle_peak_ids`).
        - BLUE: szczyt zaliczony jednak w **starym** cyklu (jest w
          `all_climbed_peak_ids`, ale **nie** w `current_cycle_peak_ids`).
        - ORANGE: szczyt blokowany dziś (symulacja nie poprawiła licznika).
        - RED: szczyt jest *ważny* — symulacja wejścia podnosi licznik
          `valid_ascents_count`; score = `100 / missing_after_ascent`
          (lub 100, gdy już dostateczne).

        Args:
          version: wersja regulaminu odznaki (agregat domenowy).
          domain_ascents: wejścia w obecnym cyklu (już przefiltrowane).
          peak_id: szczyt, którego wartaść symulujemy.
          today_date: data, z którą symulujemy nowe wejście.
          current_cycle_peak_ids: szczyty wejść w obecnym cyklu (z `domain_ascents`).
          all_climbed_peak_ids: **wszystkie** szczyty, które turysta kiedykolwiek
            zdobył (do rozróżnienia GREEN vs BLUE).
          context: kontekst weryfikacyjny (wiek, kluby, itp.).
          current_valid_count: licznik ważnych wejść *bez* szczytu `peak_id`.

        Returns:
          PeakSimulationResult z kolorem i scorem.
        """
        if not version.pool_peak_ids:
            return PeakSimulationResult(color="GRAY", score=0)

        # GREEN: już wejście w obecnym cyklu
        if peak_id in current_cycle_peak_ids:
            return PeakSimulationResult(color="GREEN", score=0)

        # BLUE: wejście w starym cyklu (poza obowiązującym)
        if peak_id in all_climbed_peak_ids:
            return PeakSimulationResult(color="BLUE", score=0)

        # Symulacja: "A co, gdyby turysta wszedł tu dzisiaj?"
        sim_ascent = Ascent(peak_id=peak_id, ascent_date=today_date, region_ids=frozenset())
        sim_eval = version.evaluate(domain_ascents + [sim_ascent], context)
        sim_valid_count = sim_eval.valid_ascents_count

        if sim_valid_count > current_valid_count:
            # Szczyt jest ważny! Obliczamy punkty.
            pending_tier = next((t for t in sim_eval.tiers if t.status != "COMPLETED"), None)
            target = pending_tier.required_count if pending_tier else len(version.pool_peak_ids)
            missing_after_ascent = max(target - sim_valid_count, 0)

            score = 100 if missing_after_ascent == 0 else round(100.0 / missing_after_ascent)
            return PeakSimulationResult(color="RED", score=score)

        # Symulacja nie poprawiła licznika → blokada na dziś
        return PeakSimulationResult(color="ORANGE", score=0)
