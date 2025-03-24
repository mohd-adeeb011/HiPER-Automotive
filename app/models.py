from datetime import datetime
from pydantic import BaseModel
from typing import Dict

class UploadSession(BaseModel):
    user_id: str
    filename: str
    total_size: int
    next_expected_byte: int = 0
    status: str  # 'pending' or 'complete'
    temp_file: str
    last_updated: datetime

_db: Dict[str, UploadSession] = {}

def get_db() -> Dict[str, UploadSession]:
    return _db

def update_db(key: str, session: UploadSession):
    _db[key] = session

def delete_from_db(key: str):
    if key in _db:
        del _db[key]