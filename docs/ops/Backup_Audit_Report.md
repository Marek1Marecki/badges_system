# Ops — Audit Obowiązków Backupowych (Luki i Limity)

> **Cel:** Zidentyfikowanie luk w strategii backupów, szczególnie dla środowisk DEV/TEST i danych referencyjnych.
> **Powstało na podstawie:** Przeglądu `scripts/dev-backup.sh`, `ADR-021`, `ADR-023`, workflowów CI/CD.
> **Status:** `draft` — do omówienia z SRE i administratorem.

---

## 1. TL;DR — Co jest chronione, a co nie

| Warstwa | Chroniona? | Jak | Braki |
|---|---|---|---|
| **Baza danych PROD** | ✅ Tak | Codzienny `pg_dump -Fc` do S3 (ADR-021) | Brak PITR |
| **Dane referencyjne** (`data/reference/`) | ✅ Tak (wersjonowane w Git) | Snapshot JSON+GZIP, manifest z `sha256` | Brak automatycznego snapshotu z DEV |
| **Baza DEV / TEST** | ❌ **NIE** | Ręczne skrypty `dev-backup.sh` | **Brak automatyzacji, brak retencji** |
| **Redis cache** | ❌ Nie | Ephemerally (zgodnie z ADR-021) | — (to celowe) |
| **Pliki statyczne użytkownika** | ❌ Nie | Delegowane do S3 (US-D04) | — (to celowe) |

---

## 2. Luka główna: Brak automatycznego backupu DEV/TEST

### Stan obecny
- Skrypty `scripts/dev-backup.sh` i `scripts/dev-restore.sh` **istnieją** i są **ręczne**.
- Brak workflow CI/CD uruchamiającego `dev-backup.sh` z `schedule`-triggerem.
- Brak crona na self-hosted runnerze (`crontab -l` → pusty).
- Brak systemd timerów dla tego projektu (`systemctl list-timers` → brak timerów aplikacji).
- Brak workflow `prod-backup.yml` (wspomnianego w DR Plan) — sprawdzić w `.github/workflows/`.

### Ryzyka
1. **Utrata danych deweloperskich** — przypadkowe usunięcie profilu, błąd migracji na DEV może zniszczyć cały dzień pracy.
2. **Brak punktu przywrócenia** po nieudanej migracji schematu (ADR-021 punkt 5 dotyczy tylko PROD).
3. **Zależność od pamięci operacyjnej** — ktoś musi pamiętać, żeby ręcznie backupować.

### Rekomendowane działania
1. **GitHub Actions workflow `dev-backup.yml`** z `schedule: cron` uruchamiający `dev-backup.sh` codziennie o 03:00 UTC.
2. **Automatyczny upload artefaktu** przy użyciu `actions/upload-artifact@v4`.
3. **Retencja:** 7 dni w workflow (przez `retention-days`).
4. **Opcjonalnie:** Cron na self-hosted runnerze jako warstwa awaryjna.

---

## 3. Luka: Snapshoty danych referencyjnych nie są archiwizowane w CI

### Stan obecny
- `export_reference_data.py` (ADR-023 punkt 3) jest uruchamiany **ręcznie** na DEV.
- Snapshot trafia do `data/reference/` i jest commitowany do Git.
- **Brak workflow**, które automatycznie generowałoby snapshot po merge do `main`.

### Ryzyka
1. **Drift danych** — jeśli ktoś zmodyfikuje DEV bez commita snapshotu, inni developerzy mogą mieć nieaktualne dane.
2. **Brak audytu zmian** — nie ma automatycznego triggera, który mógłby zweryfikować integralność nowego snapshotu.

### Rekomendowane działania
1. **Workflow `reference-data-release.yml`** uruchamiany ręcznie (`workflow_dispatch`) po merge do `main`.
2. Workflow uruchamia `export_reference_data`, commituje snapshot do `data/reference/`, i tworzy Pull Request do `main`.
3. CI waliduje manifest i sumy kontrolne przed akceptacją.

---

## 4. Luka: Brak workflow `prod-backup.yml`

### Stan obecny
- `Disaster_Recovery_Plan.md` sekcja 2 odnosi się do workflow `prod-backup.yml`, ale **plik nie istnieje**.

### Ryzyka
- **PROD nie ma automatycznego backupu** — to najpoważniejsza luka, naruszająca ADR-021 (RPO 24h).

### Rekomendowane działania
1. Utworzyć workflow `prod-backup.yml` z `schedule: cron` codziennie o 02:00 UTC.
2. Workflow używa konta `backup-writer-prod` i wywołuje dedykowany skrypt `prod-backup.sh`.
3. Wymagane jest utworzenie `scripts/prod-backup.sh` (sekcja 7 DR Plan to otwarte zadanie).

---

## 5. Podsumowanie — Luki vs ADR-021/023

| Wymaganie (ADR) | Status | Uwagi |
|---|---|---|
| ADR-021: Codzienny backup PROD → S3 | ❌ **Nie spełnione** | Workflow `prod-backup.yml` nie istnieje |
| ADR-021: Przed migracją → backup | ❌ Częściowo | Tylko ręczne `dev-backup.sh` |
| ADR-021: Kwartalny DR Drill | ❌ Nie ma automatyzacji | To jednorazowa procedura |
| ADR-023: Eksport snapshotu z DEV | ⚠️ Ręczny | Brak CI triggera po merge |
| ADR-023: Walidacja snapshotu w CI | ⚠️ Ręczna | Wymaga ręcznego uruchomienia `validate_reference_manifest` |

---

## 6. Proponowany plan działań (najwyższy priorytet)

| Priorytet | Zadanie | Osaczenie |
|---|---|---|
| **🔴 Krytyczny** | Utworzyć workflow `prod-backup.yml` + `scripts/prod-backup.sh` | 3–5 dni |
| **🟡 Wysoki** | Workflow `dev-backup.yml` z `schedule` + artefaktami | 1 dzień |
| **🟡 Wysoki** | Workflow `reference-data-release.yml` (manual trigger po merge) | 2 dni |
| **🟢 Niski** | Cron fallback na self-hosted runnerze `pc-dev-runner` | 0.5 dnia |

---

## 7. Powiązane dokumenty
- **ADR-021** — Strategia Backupów i Disaster Recovery (definicja RPO/RTO, S3, 3-2-1).
- **ADR-023** — Cykl Życia Danych Referencyjnych.
- **docs/ops/Disaster_Recovery_Plan.md** — Procedury odtwarzania dla PROD.
- **scripts/dev-backup.sh** | **scripts/dev-restore.sh** — ręczne skrypty deweloperskie.