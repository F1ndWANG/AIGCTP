from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class TaskRunResponse(BaseModel):
    task_id: str
    session_id: str
    task_type: str
    status: str
    input: dict[str, Any]
    result: dict[str, Any]
    error: str = ""
    retry_count: int
    max_retries: int
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DomainEventResponse(BaseModel):
    event_id: str
    session_id: str
    task_id: Optional[str] = None
    event_type: str
    aggregate_type: str = ""
    aggregate_id: str = ""
    payload: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}
