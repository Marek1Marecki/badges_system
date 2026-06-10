# DataFrame Contract

**Status:** Architektoniczny  
**Zakres:** Wszystkie projekty używające Pandas

---

## Filozofia

DataFrame jest strukturą transportową — nie obiektem domenowym, nie miejscem logiki biznesowej.

**Zasada:** Każdy DataFrame przekraczający granicę warstwy musi mieć jawny schemat walidacyjny (Pandera).

| DataFrame jest... | DataFrame nie jest... |
|-------------------|-----------------------|
| Nośnikiem danych między warstwami | Obiektem domenowym |
| Wejściem/wyjściem adaptera | Argumentem use case'u |
| Strukturą do walidacji | Miejscem reguł biznesowych |

---

## Zasady ogólne

### Boundary Validation (obowiązkowe)

Każdy DataFrame wczytany z zewnętrznego źródła musi zostać zwalidowany przez Pandera **natychmiast po wczytaniu** — przed jakimkolwiek użyciem:

- Plik CSV/Excel
- Google Sheets API
- REST API zwracające dane tabelaryczne
- Zapytanie do bazy danych

```python
# infrastructure/adapters/persistence/measurements_adapter.py
class MeasurementsAdapter:
    def fetch(self) -> pd.DataFrame:
        df = self._read_from_source()
        return MeasurementsSchema.validate(df)  # Fail-fast — natychmiast
```

### Zakaz w `domain/`

DataFrame nigdy nie wchodzi do `domain/`. Musi zostać przekształcony do:
- DTO (Pydantic) — dla pojedynczych rekordów
- Value Objects — dla typów domenowych
- List encji — dla kolekcji

### Fail-Fast — bez silent correction

```python
# Zakaz:
df["systolic"] = df["systolic"].fillna(0)  # maskuje błąd danych
df = df.dropna()                            # cicha korekta

# Nakaz:
MeasurementsSchema.validate(df)             # błąd → wyjątek → zatrzymanie
```

Brak danych lub błędny typ → wyjątek z precyzyjnym wskazaniem wiersza i kolumny.

---

## Schemat minimalny (wymagany)

Każdy schemat Pandera musi definiować dla każdej kolumny:

| Element | Wymagany | Przykład |
|---------|----------|---------| 
| Typ danych | ✅ | `pa.Column(int)` |
| Nullable | ✅ | `nullable=False` |
| Zakres (dla liczb) | ✅ | `pa.Check.between(60, 250)` |
| Unikalność (dla identyfikatorów) | jeśli dotyczy | `unique=True` |

---

## Wzorzec implementacji

### Schemat w `infrastructure/adapters/`

```python
# infrastructure/adapters/persistence/measurements_schema.py
import pandera as pa
from pandera.typing import DataFrame, Series

class MeasurementsSchema(pa.DataFrameModel):
    date: Series[pa.DateTime] = pa.Field(nullable=False)
    systolic: Series[int] = pa.Field(nullable=False, ge=60, le=250)
    diastolic: Series[int] = pa.Field(nullable=False, ge=40, le=150)
    pulse: Series[int] = pa.Field(nullable=False, ge=30, le=220)

    @pa.check("systolic", name="systolic_greater_than_diastolic")
    def systolic_above_diastolic(cls, systolic: Series[int]) -> Series[bool]:
        return systolic > cls.diastolic  # type: ignore[attr-defined]

    class Config:
        coerce = False  # Zakaz cichego rzutowania typów
        strict = True   # Zakaz nieznanych kolumn
```

### Mapowanie DataFrame → DTO w `application/`

```python
# application/use_cases/analyze_measurements.py
class AnalyzeMeasurements:
    def execute(self, df: pd.DataFrame) -> list[MeasurementDTO]:
        # DataFrame już zwalidowany przez adapter
        return [
            MeasurementDTO(
                date=row["date"],
                systolic=row["systolic"],
                diastolic=row["diastolic"],
                pulse=row["pulse"],
            )
            for _, row in df.iterrows()
        ]
        # Od tego momentu — tylko DTO, zero DataFrame w domenie
```

---

## Warstwowanie

| Warstwa | Status DataFrame | Obowiązki |
|---------|-----------------|-----------| 
| `infrastructure/adapters/` | ✅ Natywny | Wczytanie + walidacja Pandera |
| `application/` | ⚠️ Tranzytowy | Może przyjąć zwalidowany DataFrame, mapuje do DTO |
| `domain/` | ❌ Zakaz | Nigdy nie widzi DataFrame |
| `tests/` | ✅ Dozwolony | Tworzenie fixtures, testowanie schematów |

---

## Testowanie schematów

```python
# tests/unit/infrastructure/test_measurements_schema.py
from faker import Faker
import pandas as pd
import pytest
from infrastructure.adapters.persistence.measurements_schema import MeasurementsSchema

fake = Faker()

def make_valid_df(n: int = 5) -> pd.DataFrame:
    rows = []
    for _ in range(n):
        dia = fake.random_int(min=60, max=110)
        sys = dia + fake.random_int(min=10, max=50)
        rows.append({
            "date": fake.date_time_this_year(),
            "systolic": sys,
            "diastolic": dia,
            "pulse": fake.random_int(min=50, max=100),
        })
    return pd.DataFrame(rows)

def test_valid_dataframe_passes():
    MeasurementsSchema.validate(make_valid_df())

def test_invalid_type_raises():
    df = make_valid_df()
    df["systolic"] = "not_a_number"
    with pytest.raises(Exception):
        MeasurementsSchema.validate(df)

def test_out_of_range_raises():
    df = make_valid_df()
    df.loc[0, "systolic"] = 300  # Powyżej maksimum
    with pytest.raises(Exception):
        MeasurementsSchema.validate(df)
```

---

## Tryby walidacji

**Light Tier (minimum):** Walidacja tylko przy wczytaniu z zewnętrznego źródła.

**Enterprise Tier:** Walidacja przy wczytaniu **i** przed zapisem do trwałego storage:

```python
def save_measurements(self, df: pd.DataFrame) -> None:
    MeasurementsSchema.validate(df)  # walidacja przed zapisem
    self._write_to_storage(df)
```
