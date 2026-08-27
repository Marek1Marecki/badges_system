"""Linter migracji — statyczna introspekcja `Migration.operations` względem whitelisty dozwolonych operacji (ADR-024,
pkt 6).

UMIEJSCOWIENIE: ten plik NIE jest częścią repozytorium infrastruktury —
skopiuj go do tej samej aplikacji Django, w której już macie
`restore_reference_data.py` (sądząc po grupie `[badges]` w `manage.py help`,
prawdopodobnie: `badges/management/commands/lint_migrations.py` lub
`apps/badges/management/commands/lint_migrations.py`).

Aby znaleźć dokładną ścieżkę u siebie:
    docker compose exec web find / -name "restore_reference_data.py" -not -path "*/.venv/*" 2>/dev/null

Semantyka (zgodna z ADR-024):
- BLOCKED (RemoveField, DeleteModel) -> exit 1, zatrzymuje Database Release.
  Te operacje nie mogą znaleźć się w tym samym wydaniu, w którym struktura
  przestaje być używana (Zasada Migracji Destrukcyjnych).
- REVIEW (AlterField, RenameField, RunSQL, RunPython) -> tylko raportowane,
  NIE blokuje. Zatwierdzenie tych operacji jest odpowiedzialnością Pull
  Requestu (code review), nie tego skryptu uruchamianego przy każdym
  Database Release — linter przy deployu nie ma jak automatycznie ocenić,
  czy review się odbyło.
- ALLOWED (CreateModel, AddField z null=True/wartością domyślną) -> bez akcji.

WAŻNE: sprawdzane są WYŁĄCZNIE migracje aplikacji "pierwszej strony" —
takich, których kod fizycznie leży wewnątrz `settings.BASE_DIR` (czyli
Waszego repozytorium, np. `/app`). Migracje zależności zewnętrznych
(`django.contrib.*`, `django_celery_beat`, `allauth` i inne pakiety z
`/opt/venv/.../site-packages/`) są ŚWIADOMIE WYKLUCZONE z tej kontroli —
ADR-024 kontroluje to, co PISZE ten zespół, nie historyczne migracje
maintainerów pakietów zewnętrznych, które i tak trzeba zastosować, żeby
te pakiety w ogóle działały. Rozróżnienie działa "za darmo" dzięki temu, że
Dockerfile trzyma `/opt/venv` całkowicie poza `/app` (patrz
`UV_PROJECT_ENVIRONMENT=/opt/venv`) — bez tego rozróżnienia świeże
środowisko z `django-celery-beat`/`django.contrib.contenttypes` NIGDY nie
przeszłoby tego lintera, niezależnie od tego, co napisze ten zespół.

To narzędzie jest DRUGĄ linią obrony (uruchamianą przez
scripts/release-database.sh bezpośrednio przed `migrate`), nie zastępuje
kontroli w CI na etapie PR — patrz README-infra.md, sekcja "Znane luki".
"""

from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import migrations
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.operations.base import Operation

REVIEW_REQUIRED = (
    migrations.AlterField,
    migrations.RenameField,
    migrations.RunSQL,
    migrations.RunPython,
)
BLOCKED = (
    migrations.RemoveField,
    migrations.DeleteModel,
)


class Command(BaseCommand):
    """Komenda do lintowania migracji."""

    help = (
        "Statyczna introspekcja plików migracji względem whitelisty "
        "dozwolonych operacji (ADR-024, pkt 6). Kod wyjścia != 0 wyłącznie "
        "przy wykryciu operacji z kategorii BLOCKED (RemoveField/DeleteModel). "
        "Sprawdzane są wyłącznie aplikacje pierwszej strony (kod wewnątrz "
        "BASE_DIR) — zależności zewnętrzne są pomijane."
    )

    def add_arguments(self, parser):
        """

        Args:
          parser:

        Returns:

        """
        parser.add_argument(
            "--app-label",
            action="append",
            dest="app_labels",
            default=None,
            help=(
                "Ogranicz sprawdzenie do wskazanej aplikacji (można podać "
                "wielokrotnie, w tym aplikacji zewnętrznych — jawne podanie "
                "tą flagą omija automatyczne wykluczanie spoza BASE_DIR). "
                "Domyślnie: wszystkie aplikacje pierwszej strony."
            ),
        )
        parser.add_argument(
            "--verbose-skip",
            action="store_true",
            default=False,
            help="Wypisz listę aplikacji pominiętych jako zewnętrzne (diagnostyka).",
        )

    def handle(self, *args, **options):
        """

        Args:
          *args:
          **options:

        Returns:

        """
        # `connection=None` — celowo nie łączymy się z bazą. Ten linter
        # sprawdza TREŚĆ plików migracji na dysku, nie stan konkretnej bazy
        # danych (ten sam wynik niezależnie od środowiska — wymóg
        # deterministyczności z ADR-024, "linter musi być deterministyczny").
        loader = MigrationLoader(connection=None, load=True)

        requested_labels = options.get("app_labels")
        if requested_labels:
            # Jawne żądanie z CLI omija filtrowanie po ścieżce — jeśli ktoś
            # naprawdę chce sprawdzić aplikację zewnętrzną, może to wymusić.
            app_labels = set(requested_labels)
        else:
            app_labels, skipped_vendor = self._first_party_app_labels(loader)
            if options.get("verbose_skip") and skipped_vendor:
                self.stdout.write(
                    f"Pomijam {len(skipped_vendor)} aplikacji spoza BASE_DIR "
                    f"(zależności zewnętrzne): {', '.join(sorted(skipped_vendor))}"
                )

        blocked_found: list[tuple[str, str]] = []
        review_found: list[tuple[str, str]] = []

        for (app_label, migration_name), migration in loader.disk_migrations.items():
            if app_label not in app_labels:
                continue
            location = f"{app_label}.{migration_name}"
            for operation in migration.operations:
                classification, detail = self._classify(operation)
                if classification == "blocked":
                    blocked_found.append((location, detail))
                elif classification == "review":
                    review_found.append((location, detail))

        if review_found:
            self.stdout.write(
                self.style.WARNING(
                    f"\n{len(review_found)} operacja(e) z kategorii "
                    "'wymaga code review' (oczekiwane, jeśli PR już to "
                    "zatwierdził — ten linter tego nie weryfikuje):"
                )
            )
            for location, detail in review_found:
                self.stdout.write(f"  - {location}: {detail}")

        if blocked_found:
            self.stdout.write(
                self.style.ERROR(
                    f"\n{len(blocked_found)} ZABLOKOWANA(YCH) operacja(i) "
                    "migracji (ADR-024 — Zasada Migracji Destrukcyjnych):"
                )
            )
            for location, detail in blocked_found:
                self.stdout.write(f"  - {location}: {detail}")
            raise CommandError(
                f"Linter migracji: {len(blocked_found)} zablokowana(ych) operacja(i). Database Release zatrzymany."
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Linter migracji: OK ({len(app_labels)} aplikacji sprawdzonych, "
                f"{len(review_found)} do code review, 0 zablokowanych)."
            )
        )

    @staticmethod
    def _first_party_app_labels(loader: MigrationLoader) -> tuple[set, set]:
        """Zwraca (aplikacje_pierwszej_strony, aplikacje_pominięte).

        Rozróżnienie odbywa się po lokalizacji kodu aplikacji na dysku, nie
        po tym, czy aplikacja jest "wasza" w jakimś innym sensie — kod
        aplikacji leżący fizycznie wewnątrz `settings.BASE_DIR` jest
        traktowany jako pierwsza strona, wszystko poza (typowo:
        `/opt/venv/.../site-packages/`) jako zależność zewnętrzna.

        Działa to niezawodnie w tym projekcie dzięki decyzji z Dockerfile:
        `UV_PROJECT_ENVIRONMENT=/opt/venv` trzyma zależności całkowicie poza
        `/app` — bez tego rozdzielenia ta heurystyka mogłaby dawać fałszywe
        wyniki (np. gdyby zależności instalowały się do `.venv` wewnątrz
        katalogu projektu).

        Args:
          loader: MigrationLoader:
          loader: MigrationLoader:

        Returns:
        """
        try:
            base_dir = Path(str(settings.BASE_DIR)).resolve()
        except Exception as exc:  # noqa: BLE001 — chcemy czytelny komunikat, nie traceback
            raise CommandError(
                f"Nie udało się odczytać settings.BASE_DIR: {exc}. "
                "Ten linter wymaga, żeby BASE_DIR wskazywał na katalog "
                "repozytorium (standardowa konwencja Django)."
            ) from exc

        migrated = set(loader.migrated_apps)
        first_party: set = set()
        vendor: set = set()

        for cfg in apps.get_app_configs():
            if cfg.label not in migrated:
                continue
            try:
                app_path = Path(cfg.path).resolve()
            except Exception:  # noqa: BLE001 — brak ścieżki = traktuj jako vendor, nie wywalaj
                vendor.add(cfg.label)
                continue

            if app_path.is_relative_to(base_dir):
                first_party.add(cfg.label)
            else:
                vendor.add(cfg.label)

        return first_party, vendor

    @staticmethod
    def _classify(operation: Operation) -> tuple[str, str]:
        """Zwraca (kategoria, opis) dla pojedynczej operacji migracji.

        Kolejność sprawdzeń ma znaczenie: BLOCKED sprawdzane jest pierwsze
        (bezwzględny priorytet), potem szczególny przypadek AddField
        (wymaga zbadania pola, nie samej klasy operacji), na końcu reszta
        operacji wymagających review. Wszystko inne (w tym CreateModel)
        jest dozwolone automatycznie.

        Args:
          operation: Operation:
          operation: Operation:

        Returns:
        """
        if isinstance(operation, BLOCKED):
            return "blocked", operation.__class__.__name__

        if isinstance(operation, migrations.AddField):
            field = getattr(operation, "field", None)
            is_nullable = bool(getattr(field, "null", False)) if field else False
            has_default = field is not None and field.has_default()
            if is_nullable or has_default:
                return "allowed", "AddField (nullable lub z wartością domyślną)"
            return (
                "review",
                "AddField BEZ null=True i BEZ wartości domyślnej — ryzyko "
                "table lock na dużej tabeli (ADR-024, Zasada Expand)",
            )

        if isinstance(operation, REVIEW_REQUIRED):
            return "review", operation.__class__.__name__

        return "allowed", operation.__class__.__name__
