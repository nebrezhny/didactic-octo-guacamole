from pydantic import BaseModel, ConfigDict
from datetime import datetime, date
from uuid import UUID

class User(BaseModel):
    user_id: int
    username: str | None = None
    first_name: str | None = None
    country: str | None = None
    created_at: datetime | None = None
    free_requests_today: int = 0
    last_reset_date: date | None = None
    plan: str = "free"
    plan_requests_left: int = 0
    plan_expires_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

class RequestLog(BaseModel):
    id: UUID | None = None
    user_id: int
    subject: str | None = None
    input_type: str
    question: str | None = None
    answer: str | None = None
    tokens_used: int | None = None
    cost_usd: float | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

class Payment(BaseModel):
    id: UUID | None = None
    user_id: int
    stars_amount: int
    plan: str
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
