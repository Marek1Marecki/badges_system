"""Skrypt kontrolny wyświetlający przypisane obiekty i stopnie dla każdej odznaki."""

import os
import sys

# Inicjalizacja środowiska Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()


def generate_report() -> None:
    """Generuje raport o odznakach, ich wersjach, stopniach i puli obiektów."""
    from apps.badges.models import BadgeModel

    # Pobieramy wszystkie odznaki wraz z powiązanymi danymi (optymalizacja zapytań)
    badges = BadgeModel.objects.prefetch_related("versions", "versions__pool_peaks", "versions__tiers").order_by("name")

    if not badges.exists():
        print("Brak zdefiniowanych odznak w bazie danych.")
        return

    print(f"\nZnaleziono {badges.count()} zdefiniowanych odznak:\n")

    for badge in badges:
        print("=" * 60)
        print(f"ODZNAKA: {badge.name} [{badge.code}]")
        organizer_name = badge.organizer.name if badge.organizer else "Brak organizatora"
        print(f"Organizator: {organizer_name}")
        print("=" * 60)

        versions = badge.versions.all()
        if not versions:
            print("  -> Brak zdefiniowanych wersji regulaminu!\n")
            continue

        for version in versions:
            print(f"  Wersja: {version.version_code} (Obowiązuje od: {version.valid_from})")

            # ==========================================
            # NOWE: REGUŁY BIZNESOWE (JSON)
            # ==========================================
            rules = version.rules
            if rules:
                print("  Reguły biznesowe:")
                for rule in rules:
                    # Kopiujemy słownik, by bezpiecznie usunąć i wypisać 'type'
                    rule_data = dict(rule)
                    rule_type = rule_data.pop("type", "Nieznany typ")

                    # Jeśli reguła ma dodatkowe parametry (np. limit_in_years=3), łączymy je w ładny string
                    params = [f"{k}={v}" for k, v in rule_data.items() if v]
                    params_str = f" (Parametry: {', '.join(params)})" if params else ""

                    print(f"    [+] {rule_type}{params_str}")
            else:
                print("  Reguły biznesowe: Brak dodatkowych ograniczeń (wystarczy samo wejście)")
            print("")  # Pusta linia dla czytelności

            # STOPNIE (Tiers)
            tiers = version.tiers.all()
            if tiers:
                print("  Stopnie:")
                for tier in tiers:
                    req = tier.required_peaks_count
                    req_str = f"wymaga {req} obiektów" if req else "wymaga WSZYSTKICH obiektów z puli"
                    print(f"    - {tier.get_name_display()} (Kolejność: {tier.order}) -> {req_str}")
            else:
                print("    - UWAGA: Brak zdefiniowanych stopni!")

            # PULA SZCZYTÓW (Pool Peaks)
            peaks = version.pool_peaks.all().order_by("name")
            print(f"\n  Pula obiektów (Razem: {peaks.count()}):")

            if not peaks:
                print("    - UWAGA: Pula obiektów jest pusta!\n")
            else:
                for peak in peaks:
                    alt_str = f" ({peak.altitude}m)" if peak.altitude else ""
                    print(f"    * {peak.name}{alt_str} [{peak.type}]")

            print("-" * 60)
        print("\n")


if __name__ == "__main__":
    generate_report()
