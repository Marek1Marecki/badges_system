"""Adapter Repo implementujący BadgeRepositoryPort dla Django ORM."""

from datetime import datetime

from application.ports.badge_repository_port import BadgeRepositoryPort
from apps.badges.models import BadgeVersionModel
from domain.entities.badge_version import BadgeVersionDomain
from domain.rules.badge_rules import (
    ActivityRule,
    BadgeRule,
    GroupedAlternativesRule,
    MandatoryObjectsRule,
    MinAgeRule,
    RequiresClubJoinDateRule,
    StartDateRule,
    TimeLimitRule,
)
from domain.value_objects.ascent import ActivityType

# Rejestr tłumaczący string z bazy danych (z pola JSON)
# na klasę strategii z warstwy domeny
RULE_REGISTRY = {
    "ActivityRule": ActivityRule,
    "TimeLimitRule": TimeLimitRule,
    "RequiresClubJoinDateRule": RequiresClubJoinDateRule,
    "MinAgeRule": MinAgeRule,
    "StartDateRule": StartDateRule,
    "MandatoryObjectsRule": MandatoryObjectsRule,
    "GroupedAlternativesRule": GroupedAlternativesRule,
}


class DjangoBadgeRepository(BadgeRepositoryPort):
    """Implementuje komunikację z bazą relacyjną przy użyciu Django ORM."""

    def get_badge_version(self, badge_code: str, version_code: str) -> BadgeVersionDomain | None:
        """Pobiera odznakę z bazy i rekonstruuje czysty agregat domenowy (Hydracja)."""
        try:
            # Prefetch_related zapobiega problemom n+1 przy dociąganiu szczytów
            version_model = BadgeVersionModel.objects.prefetch_related("pool_peaks").get(
                badge__code=badge_code, version_code=version_code
            )
        except BadgeVersionModel.DoesNotExist:
            return None

        # 1. Hydracja ZBIORU szczytów z tabeli relacyjnej
        pool_peaks = {peak.id for peak in version_model.pool_peaks.all()}

        # Ustalenie required_count na podstawie poziomy stopnia (Tiers)
        # Tutaj wprowadzimy małą zmianę dla Fazy C, bo Stopień dziedziczy teraz z Wersji.
        # W tym adapterze (pobierającym samą Wersję), na razie ustawiamy domyślnie pulę całkowitą,
        # dopóki nie rozszerzymy interfejsu Portu o pobieranie konkretnego Stopnia.
        req_count = len(pool_peaks)

        # 2. Hydracja STRATEGII z pola JSON
        domain_rules: list[BadgeRule] = []

        for rule_dict in version_model.rules:
            data = dict(rule_dict)
            rule_type = data.pop("type")

            # 1. Reguła aktywności (z ominięciem problematycznej składni)
            if rule_type == "ActivityRule":
                activities_set = set()
                if "allowed_activities" in data:
                    for act_str in data["allowed_activities"]:
                        activities_set.add(ActivityType(act_str))
                domain_rules.append(ActivityRule(allowed_activities=activities_set))

            # 2. Reguła limitu czasu
            elif rule_type == "TimeLimitRule":
                limit_val = data.get("limit_in_years", 0)
                domain_rules.append(TimeLimitRule(limit_in_years=int(limit_val)))

            # 3. NASZA NOWA REGUŁA (Klub KGP)
            elif rule_type == "RequiresClubJoinDateRule":
                domain_rules.append(RequiresClubJoinDateRule())

            # 4. NASZA NOWA REGUŁA (Minimalny wiek)
            elif rule_type == "MinAgeRule":
                age_val = data.get("min_age", 0)
                domain_rules.append(MinAgeRule(min_age=int(age_val)))

            # 5. NASZA NOWA REGUŁA: Zalicza od daty
            elif rule_type == "StartDateRule":
                date_str = data.get("start_date")
                if date_str:
                    try:
                        # Przetwarzamy tekst "YYYY-MM-DD" na obiekt datetime.date
                        parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                        domain_rules.append(StartDateRule(start_date=parsed_date))
                    except ValueError:
                        pass  # Zignoruj błędny format daty

            # 6. NASZA NOWA REGUŁA: Obowiązkowe szczyty
            elif rule_type == "MandatoryObjectsRule":
                raw_ids = data.get("mandatory_peak_ids")
                if raw_ids:
                    # Zamieniamy listę z JSON-a na zbiór (Set) integerów dla szybszych obliczeń w Domenie
                    mandatory_ids_set = {int(pid) for pid in raw_ids}
                    domain_rules.append(MandatoryObjectsRule(mandatory_peak_ids=mandatory_ids_set))

            # 7. NASZA NOWA REGUŁA: Wiaderka (Grupy z alternatywami)
            elif rule_type == "GroupedAlternativesRule":
                min_req = data.get("min_groups_required")
                raw_groups_list = data.get("groups")

                # Upewniamy się, że mamy wymagane dane
                if min_req is not None and raw_groups_list is not None:
                    domain_groups = []

                    for group_dict in raw_groups_list:
                        peak_ids = group_dict.get("peak_ids")

                        if peak_ids:
                            # Tworzymy zbiór dla tego konkretnego "wiaderka"
                            bucket_set = set()
                            for pid in peak_ids:
                                bucket_set.add(int(pid))

                            domain_groups.append(bucket_set)

                    # Jeśli udało się stworzyć jakiekolwiek wiaderka, dodajemy regułę
                    if domain_groups:
                        rule_obj = GroupedAlternativesRule(groups=domain_groups, min_groups_required=int(min_req))
                        domain_rules.append(rule_obj)

            # Na koniec zwracamy gotowy, odtworzony obiekt domeny
        req_count = len(pool_peaks)

        return BadgeVersionDomain(
            version_id=version_model.version_code,
            rules=domain_rules,
            pool_peak_ids=pool_peaks,
            required_count=req_count,
        )
