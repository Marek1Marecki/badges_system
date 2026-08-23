# Security Backlog

Rejestr wszystkich CVE znalezionych w skanach Trivy w fazie development.
Backlog jest przeglądany co 2–4 tygodnie.

Priorytet:
1. `affected` + dostępny fix
2. `fix_deferred`
3. `will_not_fix`

## Obecny stan (2026-08-23)

### Podsumowanie

| Kategoria | Liczba | Działanie |
|-----------|--------|-----------|
| CRITICAL + affected | 4 | backlog remediation |
| CRITICAL + fix_deferred | 2 | security exception |
| CRITICAL + will_not_fix | 1 | security exception |
| HIGH + affected | 57 | backlog remediation |
| HIGH + fix_deferred | 12 | security exception |
| HIGH + will_not_fix | 3 | security exception |
| **RAZEM** | **79** | — |

### CRITICAL — affected (fix dostępny, brak w Debian 12)

| CVE | Package | Action | Owner | Target |
|-----|---------|--------|-------|--------|
| CVE-2026-13221 | perl-base | CRITICAL | affected | upgrade / exception | — | 2026-10-04 |
| CVE-2023-6879 | libaom3 | CRITICAL | affected | upgrade / exception | — | 2026-10-04 |
| CVE-2025-7458 | libsqlite3-0 | CRITICAL | affected | upgrade / exception | — | 2026-10-04 |

### CRITICAL — will_not_fix

| CVE | Package | Action | Owner | Target |
|-----|---------|--------|-------|--------|
| CVE-2023-45853 | zlib1g | CRITICAL | will_not_fix | upgrade / exception | — | 2026-10-04 |

### CRITICAL — fix_deferred

| CVE | Package | Action | Owner | Target |
|-----|---------|--------|-------|--------|
| CVE-2026-6653 | libxml2 | CRITICAL | fix_deferred | upgrade / exception | — | 2026-10-04 |
| CVE-2026-42496 | perl-base | CRITICAL | fix_deferred | upgrade / exception | — | 2026-10-04 |

### HIGH — affected

| CVE | Package | Action | Owner | Target |
|-----|---------|--------|-------|--------|
| CVE-2025-68431 | libheif1 | HIGH | affected | upgrade / exception | — | 2026-10-04 |
| CVE-2026-56208 | libaom3 | HIGH | affected | upgrade / exception | — | 2026-10-04 |
| CVE-2026-49014 | gdal-data | HIGH | affected | upgrade / exception | — | 2026-10-04 |
| CVE-2026-49014 | gdal-plugins | HIGH | affected | upgrade / exception | — | 2026-10-04 |
| CVE-2026-25210 | libexpat1 | HIGH | affected | upgrade / exception | — | 2026-10-04 |
| CVE-2026-49014 | libgdal32 | HIGH | affected | upgrade / exception | — | 2026-10-04 |
| CVE-2026-48962 | perl-base | HIGH | affected | upgrade / exception | — | 2026-10-04 |
| CVE-2026-53613 | bsdutils | HIGH | affected | upgrade / exception | — | 2026-10-04 |
| CVE-2026-53613 | libblkid1 | HIGH | affected | upgrade / exception | — | 2026-10-04 |
| CVE-2026-53613 | libmount1 | HIGH | affected | upgrade / exception | — | 2026-10-04 |
| CVE-2026-53613 | libsmartcols1 | HIGH | affected | upgrade / exception | — | 2026-10-04 |
| CVE-2026-58050 | libssh2-1 | HIGH | affected | upgrade / exception | — | 2026-10-04 |
| CVE-2026-12912 | libtiff6 | HIGH | affected | upgrade / exception | — | 2026-10-04 |
| CVE-2026-53613 | libuuid1 | HIGH | affected | upgrade / exception | — | 2026-10-04 |
| CVE-2026-53613 | mount | HIGH | affected | upgrade / exception | — | 2026-10-04 |
| CVE-2026-53613 | util-linux | HIGH | affected | upgrade / exception | — | 2026-10-04 |
| CVE-2026-53613 | util-linux-extra | HIGH | affected | upgrade / exception | — | 2026-10-04 |
| CVE-2026-6276 | libcurl3-gnutls | HIGH | affected | upgrade / exception | — | 2026-10-04 |
| CVE-2026-6276 | libcurl4 | HIGH | affected | upgrade / exception | — | 2026-10-04 |
| CVE-2026-33164 | libde265-0 | HIGH | affected | upgrade / exception | — | 2026-10-04 |
| CVE-2018-11205 | libhdf5-103-1 | HIGH | affected | upgrade / exception | — | 2026-10-04 |
| CVE-2018-11205 | libhdf5-hl-100 | HIGH | affected | upgrade / exception | — | 2026-10-04 |
| CVE-2023-2953 | libldap-2.5-0 | HIGH | affected | upgrade / exception | — | 2026-10-04 |
| CVE-2025-69720 | libncursesw6 | HIGH | affected | upgrade / exception | — | 2026-10-04 |
| CVE-2026-14456 | libssl3 | HIGH | affected | upgrade / exception | — | 2026-10-04 |
| CVE-2025-69720 | libtinfo6 | HIGH | affected | upgrade / exception | — | 2026-10-04 |
| CVE-2025-69720 | ncurses-base | HIGH | affected | upgrade / exception | — | 2026-10-04 |
| CVE-2025-69720 | ncurses-bin | HIGH | affected | upgrade / exception | — | 2026-10-04 |
| CVE-2026-14456 | openssl | HIGH | affected | upgrade / exception | — | 2026-10-04 |

### HIGH — will_not_fix

| CVE | Package | Action | Owner | Target |
|-----|---------|--------|-------|--------|
| CVE-2023-39616 | libaom3 | HIGH | will_not_fix | upgrade / exception | — | 2026-10-04 |
| CVE-2025-59375 | libexpat1 | HIGH | will_not_fix | upgrade / exception | — | 2026-10-04 |
| CVE-2023-52355 | libtiff6 | HIGH | will_not_fix | upgrade / exception | — | 2026-10-04 |

### HIGH — fix_deferred

| CVE | Package | Action | Owner | Target |
|-----|---------|--------|-------|--------|
| CVE-2026-12064 | libcurl3-gnutls | HIGH | fix_deferred | upgrade / exception | — | 2026-10-04 |
| CVE-2026-12064 | libcurl4 | HIGH | fix_deferred | upgrade / exception | — | 2026-10-04 |
| CVE-2026-42497 | perl-base | HIGH | fix_deferred | upgrade / exception | — | 2026-10-04 |
| CVE-2026-41992 | gzip | HIGH | fix_deferred | upgrade / exception | — | 2026-10-04 |
| CVE-2026-54369 | libacl1 | HIGH | fix_deferred | upgrade / exception | — | 2026-10-04 |

## Klasyfikacja obszarów

| Obszar | Priorytet | Pierwsza akcja |
|--------|-----------|----------------|
| GDAL | 🔴 wysoki | ustalić dostępność fixa + rzeczywistą ekspozycję |
| perl-base | 🔴 wysoki | ustalić, dlaczego jest w production |
| libaom3/libheif1 | 🔴 wysoki | ustalić dependency chain i możliwość usunięcia |
| libcurl/OpenSSL | 🟠 średni/wysoki | ustalić źródło systemowych bibliotek |
| will_not_fix | 🟠 | formalny risk assessment |

## Proces

1. Co 2–4 tygodnie zespół przegląda ten dokument
2. Dla każdego CVE:
   - sprawdź czy pojawił się fix
   - sprawdź czy aplikacja nadal nie używa dotkniętej funkcji
   - zaktualizuj status
3. Wyjątki z przekroczonym terminem przeglądu wracają do polityki domyślnej

<!-- Last updated: 2026-08-23 from Trivy scan -->
