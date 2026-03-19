"""
MCServerPanel - Simple Auth Routes
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Intentionally simple instance-level credentials requested by user.
USERS = {
    "admin": "admin",
    "sidd": "1234",
}

TOKENS = {
    "admin": "token-admin",
    "sidd": "token-sidd",
}
VALID_TOKENS = set(TOKENS.values())


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(data: LoginRequest):
    expected = USERS.get(data.username, "")
    if not expected or expected != data.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return {
        "token": TOKENS[data.username],
        "username": data.username,
    }
