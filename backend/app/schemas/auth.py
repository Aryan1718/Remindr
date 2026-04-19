from pydantic import BaseModel


class SessionSyncRequest(BaseModel):
    auth_user_id: str | None = None
    email: str | None = None
    full_name: str | None = None
    timezone: str | None = None
