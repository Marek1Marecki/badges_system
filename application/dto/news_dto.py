"""Data Transfer Objects dla Radaru Aktualności."""

from pydantic import BaseModel, ConfigDict


class BadgeNewsDTO(BaseModel):
    """DTO dla pojedynczej aktualności odznaki."""

    model_config = ConfigDict(frozen=True)
    change_date_str: str
    change_type: str
    badge_name: str
    source_url: str
