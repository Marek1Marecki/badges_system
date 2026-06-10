# Runtime Integrity Tests

**Status:** Egzekwowalny  
**Zakres:** Obrazy produkcyjne

---

## Cel

Weryfikacja że kontener produkcyjny spełnia wymagania bezpieczeństwa i izolacji w runtime. Testy sprawdzają **konfigurację kontenera** — nie działanie aplikacji ani logikę biznesową.

---

## Zasady

- Testy są samodzielne, deterministyczne i wykonalne w CI
- Testy nie wymagają `.env.prod` ani docker-compose
- Testy nie modyfikują hosta ani kontenera
- Każdy test blokuje merge w przypadku FAIL

---

## Testy

### Test 1: Read-only filesystem — whitelist + blacklist

Sama weryfikacja whitelist bez blacklist nie jest wystarczająca — możemy wiedzieć że `/tmp` działa, ale nie wiemy czy `/app` jest naprawdę chroniony.

**Test pozytywny (whitelist) — tmpfs działa:**
```bash
docker run --rm --read-only --tmpfs /tmp app:test \
  python -c "open('/tmp/test', 'w').write('ok')"
```
FAIL jeśli zapis do `/tmp` jest niemożliwy.

**Test negatywny (blacklist) — /app jest zablokowany:**
```bash
docker run --rm --read-only --tmpfs /tmp app:test python - <<'EOF'
import sys
try:
    open("/app/test", "w")
    print("❌ SECURITY BREACH: /app is writable!")
    sys.exit(1)
except OSError:
    print("✅ /app is correctly read-only")
EOF
```
FAIL jeśli zapis do `/app` jest możliwy — naruszenie izolacji kontenera.

Poprzednie podejście (`grep -q "Read-only"`) było kruche — komunikat błędu zależy od wersji Pythona i libc. Test pythonowy łapie `OSError` niezależnie od treści komunikatu.

### Test 2: Non-root user

```bash
docker run --rm app:test id -u | grep -q '^0$' && exit 1 || echo "PASS"
```
FAIL jeśli kontener działa jako root.

### Test 3: Drop capabilities

```bash
docker run --rm --cap-drop ALL app:test python -c "print('OK')"
```
FAIL jeśli aplikacja nie startuje z minimalnymi capabilities.

### Test 4: Tmpfs

```bash
docker run --rm --read-only --tmpfs /tmp app:test \
  python -c "open('/tmp/testfile','w').write('ok')"
```
FAIL jeśli tmpfs nie działa poprawnie.

---

## Kanoniczny target Makefile

```makefile
test-runtime:
	@echo "Testing Runtime Integrity..."
	@echo "1. Whitelist — /tmp is writable"
	@docker run --rm --read-only --tmpfs /tmp $(IMAGE_NAME):latest \
	    python -c "open('/tmp/test', 'w').write('ok')" && echo "✅ PASS" || exit 1
	@echo "2. Blacklist — /app is read-only"
	@docker run --rm --read-only --tmpfs /tmp $(IMAGE_NAME):latest python - <<'EOF'
import sys
try:
    open("/app/test", "w")
    print("SECURITY BREACH: /app is writable!")
    sys.exit(1)
except OSError:
    print("✅ PASS")
EOF
	@echo "3. Non-root user"
	@docker run --rm $(IMAGE_NAME):latest id -u | grep -q '^0$$' && exit 1 || echo "✅ PASS"
	@echo "✅ All Runtime Integrity Tests passed"
```

---

## Integracja z CI (GitHub Actions)

```yaml
- name: Runtime integrity tests
  run: |
    echo "Test 1a: Whitelist — /tmp writable"
    docker run --rm --read-only --tmpfs /tmp app:test \
      python -c "open('/tmp/test', 'w').write('ok')" && echo "PASS" || exit 1

    echo "Test 1b: Blacklist — /app read-only"
    docker run --rm --read-only --tmpfs /tmp app:test python - <<'EOF'
import sys
try:
    open("/app/test", "w")
    print("SECURITY BREACH: /app is writable!")
    sys.exit(1)
except OSError:
    print("PASS")
EOF

    echo "Test 2: Non-root user"
    docker run --rm app:test id -u | grep -q '^0$' && exit 1 || echo "PASS"

    echo "Test 3: Drop capabilities"
    docker run --rm --cap-drop ALL app:test python -c "print('OK')" && echo "PASS" || exit 1
```

---

## Zakres testów

Runtime Integrity Tests sprawdzają **konfigurację kontenera i izolację**.

Nie sprawdzają:
- Działania aplikacji
- Dostępności usług sieciowych
- Poprawności logiki biznesowej

Healthcheck i testy integracyjne aplikacji należą do osobnych jobów CI.
