from fastapi import Header, HTTPException
from app.firebase_client import verify_token


async def get_current_user(authorization: str = Header(...)) -> dict:
    """Extract and verify the Firebase ID token from the Authorization header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header. Expected 'Bearer <token>'.",
        )
    token = authorization.split(" ", 1)[1]
    return await verify_token(token)
