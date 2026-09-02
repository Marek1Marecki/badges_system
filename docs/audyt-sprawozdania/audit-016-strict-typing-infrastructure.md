# Sprawozdanie AUDYT-016 — Strict Type Checking na warstwie infrastructure

> **Status:** `zrealizowany`
> **Data:** 2026-09-02
> **Obszar:** `Infrastruktura / Type Safety`
> **Priorytet:** `🟡 ŚREDNI`
> **Audytor:** Zewnętrzny Audyt Architektury (Step 3.7 Flash)
> **Autor wdrożenia:** Dominik / AI Architect

---

## 1. Kontekst i cel

### Diagnoza Audytora
Audytor zaużył, że w projekcie nie ma formalnego etapu uruchamiania `mypy --strict` na warstwie `infrastructure/`, co oznacza, że błędy typizacji (brak anotacji, nieustrukturyzowane typy generyczne, niepotrzebne `# type: ignore`) mogą przechodzić niezaubione w trybie normalnego `make check`.

### Uzasadnienie wyboru
`make check` używa konfiguracji `pyproject.toml`, gdzie:
- `disallow_untyped_defs = true` (globalnie)
- `module = ["infrastructure.*", "apps.*"]` → `disallow_untyped_defs = false`

Oznacza to, że w warstwie infrastructure typy nie są rygorystycznie wymuszane. Uruchomienie `--strict` ręcznie otwiera wszystkie flagi mypy i pozwala zobaczyć pełny obraz.

---

## 2. Co zostało wdrożone

### 2.1 Komenda diagnostyczna
```bash
make strict-infra-check
```
*(jeśli nie istnieje — użyj ręcznie poniżej)*

```bash
mypy infrastructure/ --strict
```

### 2.2 Naprawione błędy (7)

| Plik | Linia | Problem | Naprawa |
|------|-------|---------|---------|
| `infrastructure/middleware/error_handling.py` | 65, 66, 69 | 3× `# type: ignore[attr-defined]` zbędne w trybie `--strict` z projektową konfiguracją mypy | Usunięto komentarze |
| `infrastructure/adapters/celery_event_publisher.py` | 20 | `dict` bez parametrów typów | `dict[str, Any]` |
| `infrastructure/adapters/persistence/django_tourist_repo.py` | 327 | Brak anotacji parametru `progress_obj` | Doliczono `TYPE_CHECKING` import `UserBadgeProgress` i anotację |
| `application/dto/explore_queries_dto.py` | 22, 41 | `list[dict]` bez parametrów (występuje w wyniku infrastructure → application) | `list[dict[str, Any]]` |

### 2.3 Pozostałe błędy (34) — ograniczenia frameworków

Wszystkie 34 pozostałych błędów mypy `--strict` należy do **dwóch kategorii**, które **nie są błędami w naszym kodzie**, lecz ograniczeniami braku odpowiednich pluginów/stubów typów:

| Kategoria | Liczba | Przykład błędu | Przyczyna |
|-----------|--------|-----------------|-----------|
| **Django ORM: Class cannot subclass "Model" (has type "Any")** | 25 | `class TouristObject(gis_models.Model)` | Brak `mypy-django` plugin — Django ORM nie udostępnia metadanych typów dla mypy `--strict` |
| **Celery: Untyped decorator makes function "..._task" untyped** | 9 | `def fetch_osm_data_task(self, ...` | `@shared_task` z `celery` nie dostarcza informacji typów; wymagałoby to dedykowanego stubu |

> **Wnioski architektoniczne:**
> - Błędy te **nie istnieją** w `domain/` ani `application/`, które są objęte `mypy strict` w CI.
> - W warstwie `infrastructure/` **nie ma żadnych błędów typowych dla logiki biznesowej** — wszystkie 34 to `misc` / `untyped-decorator`, a nie np. `returning Any` czy `arg-type mismatch`.
> - Rozwiązanie: nie dążyć do "0 błędów --strict" na infrastructure bez wdrożenia `django-stubs` i stubów Celery — byłaby to inwestycja niespropsowa.
> - **Rekomendacja:** Dodać do roadmapy jako `AUDYT-062` — `mypy --strict infrastructure/ — PASS` (wymaga `django-stubs[mypy]`).

### 2.4 Weryfikacja
```bash
# Przed zmianą
uv run mypy infrastructure/ --strict
→ 41 errors in 13 files

# Po zmianie
uv run mypy infrastructure/ --strict
→ 34 errors in 9 files  (7 usuniętych, 34 to ograniczenia frameworków)

# make check (standardowa konfiguracja)
→ 843 passed, 1 skipped, 5/5 contracts kept
```

---

## 3. Known Limitations

| # | Ograniczenie | Wpływ | Kompensacja |
|---|--------------|-------|-------------|
| 1 | `mypy --strict infrastructure/` nie jest czysty | Nie można dodać do Gate tier (`make check`) | 7 rzeczywistych błędów naprawionych; 34 to ograniczenia frameworków. Gate tier używa standardowego `mypy` z konfiguracją projektu. |
| 2 | Django ORM bez `django-stubs` | `Class cannot subclass "Model"` | Domyślnie `infrastructure.*` ma `disallow_untyped_defs = false` |
| 3 | Celery `@shared_task` bez stubów | `Untyped decorator` | Celery taski nie przyjmują ani nie zwracają typów w sygnaturach — to naturalny brak typowalności w tej warstwie |

---

## 4. Podsumowanie

| Element | Status |
|---------|--------|
| Uruchomienie `mypy --strict` na `infrastructure/` | ✅ Wykonane |
| Naprawa 7 rzeczywistych błędów typowych | ✅ Naprawione |
| Identyfikacja 34 błędów jako ograniczenia frameworków | ✅ Zidentyfikowane i udokumentowane |
| `make check` nie zaburzone | ✅ 843 passed, 5/5 contracts |
| AUDYT-016 w `backlog_po_audycie.md` | ✅ Archiwum |
