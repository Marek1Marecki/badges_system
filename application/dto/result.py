"""DTO dla wyników operacji stanowiących Command Use Cases.

AUDYT-138: Standaryzacja wyjść Command Use Cases na spójny
obiekt `CreatedResourceResultDTO(id=...)` zamiast prymitywnych typów.
"""

from typing import Any

from pydantic import BaseModel, Field


class CreatedResourceResultDTO(BaseModel):
    """Ujednolicony wynik Command Use Case'ów modyfikujących stan.

    CQRS: komendy powinny zwracać spójny obiekt z ID utworzonego/zmodyfikowanego
    zasobu, a nie typy prymitywne (int/str/dict).
    """

    model_config = {"frozen": True}

    id: int | str = Field(description="ID utworzonego lub zmodyfikowanego zasobu")
    type: str = Field(default="resource", description="Typ zasobu (np. 'ascent', 'badge_progress')")
    extra: dict[str, Any] = Field(default_factory=dict, description="Dodatkowe pola wynikowe")
