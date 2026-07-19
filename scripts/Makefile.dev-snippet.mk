# ==============================================================================
# Makefile.dev-snippet.mk
#
# Wklej poniższy blok do głównego Makefile projektu (sekcja INFRA, zgodnie
# z 01-makefile-contract.md — prefiks nie jest tu ściśle wymagany, ale
# grupowanie z resztą targetów `docker-*`/`db-*` ma sens).
#
# CELOWO cienkie aliasy — cała logika żyje w scripts/dev-*.sh, nie tutaj.
# Zasada: Declarative Infrastructure, Imperative Operations (README-infra.md).
# Dzięki temu CI, dokumentacja i deweloper lokalnie używają dokładnie tej
# samej ścieżki wykonania, nie trzech wariantów tej samej logiki
# rozproszonych między Makefile a compose*.yml.
# ==============================================================================

.PHONY: dev-up dev-down dev-reset dev-status dev-logs

dev-up:      ## Uruchom środowisko DEV (bezpieczne na świeżym i istniejącym wolumenie)
	./scripts/dev-up.sh

dev-down:    ## Zatrzymaj środowisko DEV — NIGDY nie usuwa wolumenów z danymi
	./scripts/dev-down.sh

dev-reset:   ## DESTRUKCYJNE: usuwa wolumeny DEV i odbudowuje środowisko od zera (wymaga potwierdzenia)
	./scripts/dev-reset.sh

dev-status:  ## Diagnostyka: kontenery, PostgreSQL, Redis, migracje, Celery
	./scripts/dev-status.sh

dev-logs:    ## Podgląd logów wszystkich usług (Ctrl+C aby wyjść; opcjonalny arg = liczba linii)
	./scripts/dev-logs.sh
