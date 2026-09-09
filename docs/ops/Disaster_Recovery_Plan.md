# Ops — Disaster Recovery Plan (AUDYT-115)

> **Cel:** Operacyjny, krok-po-kroku plan dla Administratora Systemu / SRE.
> Zawiera gotowe, przetestowane komendy dla sytuacji kryzysowych:
> awaria bazy danych PROD, utrata profilu użytkownika, lub prośba o przywrócenie danych.
>
> **Opiera się na:** ADR-021 — Strategia Backupów i Disaster Recovery.
> **RPO:** 24h | **RTO:** 8h | **Retencja:** 7-dni / 4-tygodnie / 12-miesięcy

---

## 1. Kontekst i Role

### Role Operacyjne
- **Operator PROD:** Administratorem konta `backup-recovery` (S3) oraz dostępem do serwera PROD (MFA). Nie korzysta z konta `backup-writer-prod`.
- **Lead Developer / DBA:** Potwierdza każdą operację przywracania na żywo (zawsze wymagane 2-osobowy akcept).

### Co jest chronione?
- **Baza PostgreSQL (PROD):** dane użytkowników (profile, logi wejść, logistyka, ograniczenia Freemium).
- **Backupy:** codzienne zrzuty `pg_dump -Fc`, szyfrowane, do bucketu S3 z Object Lock (WORM).
- **Co NIE jest chronione:** Redis (ephemeral, rekonstruowalny z DB), pliki MFA (przechowywane w S3 zgodnie z US-D04).

---

## 2. Procedura: Codzienny Backup PROD (Automatyczny)

Backup jest uruchamiany codziennie o 02:00 UTC przez GitHub Actions (workflow `prod-backup.yml`) na koncie `backup-writer-prod`.

```bash
# Ręczna weryfikacja ostatniego backupu:
aws s3 ls s3://pttk-badges-prod-backups/ \
  --profile backup-recovery --recursive \
  --query "reverse(sort_by(Contents,&LastModified))"
```

Format nazwy pliku:
```
s3://pttk-badges-prod-backups/badges_prod_2026-09-09.dump
```

---

## 3. Procedura Awrarii: Pełna Odbudowa Bazy PROD

**Scenariusz:** Katastrofa — serwer PROD offline, baza uszkodzona.

### Krok 1: Identyfikacja ostatniego spójnego backupu
```bash
# Lista dostępnych backupów (najnowszy na górze):
aws s3 ls s3://pttk-badges-prod-backups/ --profile backup-recovery

# Wybrany plik (np. najnowszy):
BACKUP_FILE="badges_prod_2026-09-09.dump"
```

### Krok 2: Pobranie backupu na izolowany serwer DR
```bash
aws s3 cp "s3://pttk-badges-prod-backups/${BACKUP_FILE}" ./ \
  --profile backup-recovery
```

### Krok 3: Przygotowanie nowej bazy PROD
```bash
# 1. Stwórz nową instancję bazodanową PostGIS (zgodnie z ADR-026).
docker compose -f compose.prod.yml exec db \
  dropdb --if-exists "${POSTGRES_DB}"

docker compose -f compose.prod.yml exec db \
  createdb "${POSTGRES_DB}"
```

### Krok 4: Odtworzenie danych
```bash
# Zawsze przez docker compose (pg_restore WEWNĄTRZ kontenera =
# kompatybilność wersji, patrz dev-restore.sh).
docker compose -f compose.prod.yml exec -T db \
  pg_restore -U "${POSTGRES_USER}" \
  -d "${POSTGRES_DB}" \
  --clean --if-exists --no-owner \
  -j "$(nproc)" \
  < "${BACKUP_FILE}"
```

### Krok 5: Weryfikacja
```bash
# 1. Healthcheck bazy:
docker compose -f compose.prod.yml exec db pg_isready -U "${POSTGRES_USER}"

# 2. Healthcheck aplikacji:
./scripts/prod-healthcheck.sh

# 3. Reprezentatywne zapytanie:
psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
  -c "SELECT COUNT(*) FROM tourists_touristprofile;"

# 4. Test logowania użytkownika testowego:
#    → Zaloguj się przez UI jako testowy user, zweryfikuj dostęp do profilu.
```

### Krok 6: Powiadomienie
- Zaktualizuj ticket incydenta w systemie.
- Powiadom zespół ds. Produktu (Lead Developer + Product Owner).

---

## 4. Procedura: Odtworzenie pojedynczego profilu użytkownika

**Scenariusz:** Turysta usunął profil i prosi o przywrócenie.

### Krok 1: Ocena techniczna (DBA)
```bash
# 1. Czy backup z dni poprzedzającego utratę istnieje?
aws s3 ls s3://pttk-badges-prod-backups/ --profile backup-recovery

# 2. Czy profil istniał w backupie? (analiza na sandboxie)
docker run --rm -v "$(pwd):/data" postgres:18 pg_dump -Fc -t tourists_touristprofile -j 4 \
  < /data/badges_prod_2026-09-08.dump 2>/dev/null \
  | pg_restore -l | grep "touristprofile"
```

### Krok 2: Ekstrakcja (jeśli backup istnieje)
```bash
# Stwórz dedykowaną bazę danych do ekstrakcji:
docker compose -f compose.prod.yml exec -T db \
  pg_restore -U "${POSTGRES_USER}" -d postgres \
  --clean --if-exists \
  -t tourists_touristprofile -t badges_userbadgeprogress \
  < /data/badges_prod_2026-09-08.dump
```

### Krok 3: Import do PROD
```bash
# 1. Wyłącz aplikację (by uniknąć race condition):
./scripts/prod-deploy.sh --pause

# 2. Wstaw profil z sandboxa do PROD (ręczny SQL — wymaga QA):
psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
  -c "
    INSERT INTO tourists_touristprofile
    SELECT * FROM tourists_touristprofile
    WHERE user_id = <user_id_turysty>
    ON CONFLICT (id) DO UPDATE SET
      first_ascent_date = EXCLUDED.first_ascent_date,
      updated_at = NOW();
  "
```

### Krok 4: Polityka Biznesowa
- **Decyzja:** Odtworzenie pojedynczego profilu jest **możliwe** na żądanie, ale wymaga ręcznego QA i potwierdzenia Lead Developera. Jest to operacja **czasochłonna (~30–60 min)** i nie jest gwarantowana w czasie < 4h.
- **Uzasadnienie biznesowe:** Turysta niszczy swój profil rzadko. W razie problemu proponujemy regenerację konta Google + ponowne subskrypcje odznak (Prawa Nabyte mogą zostać ponownie zakotwiczone, bo są rekonstruowalne z logów wejść).

---

## 5. Procedura: Odtworzenie przed migracją schematu bazy (Ad-hoc)

Zgodnie z ADR-021, punkt 5 — backup **musi** powstać przed każdym `Database Release`.

```bash
# 1. Backup automatyczny:
aws s3 cp "s3://pttk-badges-prod-backups/badges_prod_PREDMigrate_$(date +%s).dump" \
  <(...) \
  --profile backup-writer-prod

# LUB ręczny (jeśli automatyka nie działa):
./scripts/prod-backup.sh  # → zapisuje do ./backups/
aws s3 cp ./backups/*.dump \
  s3://pttk-badges-prod-backups/ --profile backup-writer-prod
```

---

## 6. Checklist — Co zrobić w pierwszych 30 minutach kryzysu

| Krok | Akcja | Odpowiedzialny |
|------|-------|----------------|
| 1 | Zablokuj dostęp do PROD (`prod-deploy.sh --pause`) | SRE |
| 2 | Zidentyfikuj ostatni spójny backup (Krok 1 sekcji 3) | SRE |
| 3 | Potwierdź integrację ticketu z Lead Developer | SRE + Lead Dev |
| 4 | Rozpocznij procedurę odtworzenia (sekcja 3) | SRE + DBA |
| 5 | Po odtworzeniu — healthcheck + reprezentatywne zapytanie | SRE |
| 6 | Powiadom zespół Produktu | SRE |
| 7 | Zaktualizuj ticket — status ✅ Odtworzone | SRE |

---

## 7. Dług techniczny / Otwarte kwestie

- **DR Drill:** Raz na kwartał wymagana jest próba odtworzenia na odizolowanym serwerze (ADR-021, punkt 6). Wynik dokumentować w ticket systemie.
- **PITR (Point-in-Time Recovery):** Nie jest jeszcze wdrożony. Jeśli wymagania biznesowe narzuą odtworzenie do konkretnego momentu, należy rozważyć migrację na `pgBackRest` + WAL Archiving (warunek rewizji ADR-021).
- **Automatyzacja:** Skrypty `prod-backup.sh` i `prod-restore.sh` powinny zostać stworzone (na razie istnieją tylko wersje `dev-`). To otwarte zadanie w backlogu.

---

## 8. Powiązane dokumenty

- **ADR-021** — Strategia Backupów i Disaster Recovery (definicja RPO/RTO, S3, 3-2-1).
- **ADR-020** — Architektura Wdrożeń (SRE).
- **ADR-026** — PostgreSQL Volume Layout.
- **docs/Runbook.md** — Operacje codzienne, migracje schematu.
- **scripts/dev-backup.sh** | **scripts/dev-restore.sh** — wersje developerskie (referencja formatów).
