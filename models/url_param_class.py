from typing import Literal

from pydantic import BaseModel, field_validator


class URL_Params(BaseModel):
    search: str
    value: str
    condition: Literal["AND", "OR"] = "AND"

    @field_validator("condition")
    @classmethod
    def validate_condition(cls, v):
        accepted_conditions = ["AND", "OR"]
        if v is not None and not isinstance(v, accepted_conditions):
            raise ValueError(f"condition must be an element of {accepted_conditions} or None")
        return v
