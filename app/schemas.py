from pydantic import BaseModel

class User(BaseModel):
    username: str

class TokenData(BaseModel):
    username: Optional[str] = None