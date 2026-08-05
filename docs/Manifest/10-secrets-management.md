# Secrets Management

**Status:** Egzekwowalny  
**Zakres:** Wszystkie projekty

---

## Zasady ogólne

1. **Zero sekretów w repozytorium** — żadna tajna wartość nie może być w plikach wersjonowanych
2. **Tylko env vars lub secret manager** — GitHub Secrets, HashiCorp Vault, zmienne środowiskowe w CI
3. **Nie wbudowujemy w obrazy** — sekret nigdy nie jest kopiowany do warstwy obrazu Docker
4. **Idempotentny dostęp** — aplikacja może odczytać sekret wielokrotnie bez efektów ubocznych

---

## Mechanizm walidacji — `.env.example`

Każde repo zawiera plik `.env.example` z listą wymaganych kluczy (bez wartości):

```
APP_DB_PASSWORD=
API_KEY_EXTERNAL=
HF_TOKEN=
```

CI weryfikuje że wszystkie klucze z `.env.example` są dostępne jako sekrety:

```yaml
- name: Validate required secrets
  run: |
    for key in $(grep -v '^#' .env.example | grep -v '^$' | awk -F= '{print $1}'); do
      if [ -z "${!key}" ]; then
        echo "Secret $key is missing"
        exit 1
      fi
    done
```

Jeden mechanizm, zero hardkodowania, działa dla każdego projektu.

### Target `make secrets-check`

```python
# scripts/check_secrets.py
import os
import sys


def check_secrets() -> None:
    with open(".env.example") as f:
        keys = [line.split("=")[0].strip() for line in f if line.strip() and not line.startswith("#")]
    missing = [key for key in keys if not os.getenv(key)]
    if missing:
        print(f"Missing secrets: {', '.join(missing)}")
        sys.exit(1)
    print(f"All {len(keys)} secrets present.")


if __name__ == "__main__":
    check_secrets()
```

---

## Sekrety w Dockerze

- **Zakaz** używania flagi `-e` z wartością sekretu w terminalu (np. `docker run -e API_KEY=tajne`). Zostawia ślady w bash history i liście procesów (`ps aux`).
- **Dozwolone sposoby przekazywania w runtime:**
    1. Przez flagę `--env-file .env.prod` (plik musi mieć zablokowane uprawnienia `chmod 600` i być w `.gitignore`)
    2. Przez zewnętrzny system wstrzykiwania (K8s Secrets, ECS Task Definition, HashiCorp Vault)
- **Zakaz** `ENV SECRET=value` w `Dockerfile` — sekret trafia do historii warstw obrazu
- **Zakaz** instrukcji `COPY` dla plików z sekretami (`.env`, klucze SSH)
- `.env`, `.env.dev`, `.env.prod` muszą znajdować się w `.gitignore` we wszystkich repozytoriach

### Test integralności w CI

```bash
docker run --rm app:test python -c "import os; assert not os.path.exists('/app/.env')"
```

---

## Zasady dokumentacji

- `.env.example` jest commitowany i aktualny
- README zawiera informację o wymaganych sekretach
- Rotacja sekretu wymaga aktualizacji w secret managerze i CI

---

## Security-by-Default

### Zasada minimalnych uprawnień

Każdy komponent otrzymuje dostęp tylko do tego czego potrzebuje:

```python
# Zakaz — jeden klient z pełnym dostępem do wszystkiego
class GodClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("MASTER_API_KEY")
        self.db_url = os.getenv("DATABASE_URL")
        self.admin_token = os.getenv("ADMIN_TOKEN")


# Nakaz — osobne klucze per adapter, per odpowiedzialność
class ReadOnlySheetAdapter:
    def __init__(self, read_api_key: str) -> None:
        self._key = read_api_key  # tylko to co potrzebne
```

### Zakaz `eval` i dynamicznych importów

```python
# Zakaz — wykonywanie arbitralnego kodu
eval(user_input)
exec(user_input)
__import__(user_input)
importlib.import_module(config["plugin_name"])
```

Ruff wykrywa `eval`:
```toml
[tool.ruff.lint]
select = ["S"]  # flake8-bandit
# S307: Use of possibly insecure function
```

### Walidacja inputu zewnętrznego jako nieufnego

Każde dane z zewnątrz (API, plik, formularz, CLI) traktujemy jako nieufne — walidacja przez Pydantic lub Pandera **przed** użyciem:

```python
# Zakaz — użycie bez walidacji
def process(data: dict) -> None:
    meeting_id = data["id"]  # KeyError lub injection


# Nakaz — walidacja przez DTO
def process(data: dict) -> None:
    dto = MeetingInputDTO.model_validate(data)  # Pydantic raises na błędzie
    use_case.execute(dto)
```

---

## Zakazane praktyki

- Sekrety w plikach wersjonowanych (`.env`, `config.py`, `settings.py`)
- `ENV SECRET=value` w Dockerfile
- Logowanie wartości sekretów w CI
- Hardkodowane wartości sekretów w kodzie
- Wspólny `.env` dla dev i prod
