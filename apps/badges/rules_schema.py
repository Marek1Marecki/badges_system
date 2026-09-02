"""Schemat JSON dla panelu definiowania reguł odznak (django-jsonform)."""

RULES_SCHEMA = {
    "type": "list",
    "title": "Reguły Biznesowe Odznaki",
    "items": {
        "oneOf": [
            {
                "type": "dict",
                "title": "Limit Czasowy",
                "keys": {
                    "type": {"type": "string", "widget": "hidden", "default": "TimeLimitRule"},
                    "limit_in_years": {"type": "integer", "title": "Limit (w latach)"},
                },
            },
            {
                "type": "dict",
                "title": "Wymaga zapisu do Klubu",
                "keys": {
                    "type": {"type": "string", "widget": "hidden", "default": "RequiresClubJoinDateRule"},
                },
            },
            {
                "type": "dict",
                "title": "Minimalny Wiek",
                "keys": {
                    "type": {"type": "string", "widget": "hidden", "default": "MinAgeRule"},
                    "min_age": {"type": "integer", "title": "Minimalny wiek (lata)"},
                },
            },
            {
                "type": "dict",
                "title": "Szczyty zaliczane od daty",
                "keys": {
                    "type": {"type": "string", "widget": "hidden", "default": "StartDateRule"},
                    "start_date": {"type": "string", "format": "date", "title": "Data graniczna (YYYY-MM-DD)"},
                },
            },
            {
                "type": "dict",
                "title": "Obowiązkowe konkretne obiekty",
                "keys": {
                    "type": {"type": "string", "widget": "hidden", "default": "MandatoryObjectsRule"},
                    "mandatory_peak_ids": {
                        "type": "array",
                        "title": "Wpisz numery ID obiektów",
                        "items": {"type": "integer"},
                    },
                },
            },
            {
                "type": "dict",
                "title": "Wymagane obiekty z RÓŻNYCH grup (Wiaderek)",
                "keys": {
                    "type": {"type": "string", "widget": "hidden", "default": "GroupedAlternativesRule"},
                    "min_groups_required": {"type": "integer", "title": "Ile różnych grup musi zaliczyć?"},
                    "groups": {
                        "type": "array",
                        "title": "Definicje Grup (Pasm)",
                        "items": {
                            "type": "dict",
                            "keys": {
                                "group_name": {"type": "string", "title": "Nazwa grupy", "required": False},
                                "peak_ids": {"type": "array", "title": "ID obiektów", "items": {"type": "integer"}},
                            },
                        },
                    },
                },
            },
            {
                "type": "dict",
                "title": "Wymaga posiadania innej odznaki",
                "keys": {
                    "type": {"type": "string", "widget": "hidden", "default": "PrerequisiteBadgeRule"},
                    "required_badge_code": {
                        "type": "string",
                        "title": "Kod wymaganej odznaki (np. KSP)",
                        "help_text": "Wpisz kod odznaki, która jest warunkiem wstępnym.",
                    },
                },
            },
            {
                "type": "dict",
                "title": "Zamknięte Okno Czasowe (np. Jubileusz)",
                "keys": {
                    "type": {"type": "string", "widget": "hidden", "default": "DateWindowRule"},
                    "start_date": {"type": "string", "format": "date", "title": "Data początkowa (YYYY-MM-DD)"},
                    "end_date": {"type": "string", "format": "date", "title": "Data końcowa (YYYY-MM-DD)"},
                },
            },
            {
                "type": "dict",
                "title": "Maksymalny Wiek (dla dzieci/młodzieży)",
                "keys": {
                    "type": {"type": "string", "widget": "hidden", "default": "MaxAgeRule"},
                    "max_age": {"type": "integer", "title": "Maksymalny wiek (lata)"},
                },
            },
            {
                "type": "dict",
                "title": "Wymagane ilości z RÓŻNYCH podzbiorów",
                "keys": {
                    "type": {"type": "string", "widget": "hidden", "default": "MultiPoolRequirementRule"},
                    "pools": {
                        "type": "array",
                        "title": "Podzbiory (Sub-pule)",
                        "items": {
                            "type": "dict",
                            "keys": {
                                "name": {
                                    "type": "string",
                                    "title": "Nazwa grupy dla wygody (np. Tatry)",
                                    "required": False,
                                },
                                "required_count": {"type": "integer", "title": "Wymagana liczba z tej grupy"},
                                "peak_ids": {
                                    "type": "string",
                                    "title": "ID obiektów (po przecinku, np: 12, 45, 102)",
                                },
                            },
                        },
                    },
                },
            },
        ]
    },
}
