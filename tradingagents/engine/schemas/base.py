# tradingagents/engine/schemas/base.py
from __future__ import annotations
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, field_validator


class BaseSchema(BaseModel):
    model_config = ConfigDict(frozen=True)
    # frozen=True: prevents field mutation (raises ValidationError on __setattr__).
    # Does NOT auto-generate __hash__ unless hash=True is also set (it is not).
    # Do not use BaseSchema instances as dict keys or set members.

    @field_validator("*", mode="after")
    @classmethod
    def validate_utc(cls, v: object) -> object:
        # mode="after": Pydantic has already coerced ISO strings → datetime.
        # mode="before" would miss strings: isinstance("...", datetime) is False.
        if isinstance(v, datetime):
            if v.tzinfo is None:
                raise ValueError(
                    "Naive datetime detected. All datetimes must be UTC-aware."
                )
            return v.astimezone(timezone.utc)
        return v
