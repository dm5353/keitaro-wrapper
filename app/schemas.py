import re
from pydantic import BaseModel, Field, field_validator

class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=5)
    geo: str = Field(..., min_length=2)
    offer_id: int = Field(..., gt=0)
    domain_id: int | None = None
    group_id: int | None = None
    traffic_source_id: int | None = None

    @field_validator("name")
    @classmethod
    def check_name_prefix(cls, v: str) -> str:
        if not re.match(r"^test_[a-zA-Z0-9]+_.+", v):
            raise ValueError("Название должно начинаться с test_фамилия_ (например: test_ivanov_camp1)")
        return v

    def parsed_countries(self) -> list[str]:
        codes = [code.strip().upper() for code in self.geo.split(",") if code.strip()]
        if not codes:
            raise ValueError("Укажите хотя бы один код страны")
        return codes
