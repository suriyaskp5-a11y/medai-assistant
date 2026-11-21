import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from app.dependencies import get_current_user
from app.firebase_client import db
from app.schemas import (
    ConversationSummary,
    UpdateUserRequest,
    UserProfile,
    CreateConversationRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


@router.post("/auth/register", response_model=UserProfile)
async def register_user(
    body: UpdateUserRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Register or update a user profile in Firestore.
    Creates the doc if it does not exist; updates editable fields if it does.
    """
    uid = current_user["uid"]
    email = current_user.get("email", "")
    user_ref = db.collection("users").document(uid)
    snapshot = await user_ref.get()
    now = _utcnow()

    if not snapshot.exists:
        # New user — create the full document
        user_data = {
            "uid": uid,
            "email": email,
            "display_name": body.display_name or current_user.get("name"),
            "preferred_lang": body.preferred_lang or "en",
            "created_at": now,
            "updated_at": now,
        }
        await user_ref.set(user_data)
    else:
        # Existing user — only update the provided fields
        update_fields: dict = {"updated_at": now}
        if body.display_name is not None:
            update_fields["display_name"] = body.display_name
        if body.preferred_lang is not None:
            update_fields["preferred_lang"] = body.preferred_lang
        await user_ref.update(update_fields)
        existing = snapshot.to_dict()
        user_data = {**existing, **update_fields}

    return UserProfile(
        uid=user_data["uid"],
        email=user_data.get("email", email),
        display_name=user_data.get("display_name"),
        preferred_lang=user_data.get("preferred_lang", "en"),
        created_at=user_data.get("created_at"),
    )


@router.get("/users/me", response_model=UserProfile)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Return the authenticated user's profile from Firestore."""
    uid = current_user["uid"]
    user_ref = db.collection("users").document(uid)
    snapshot = await user_ref.get()

    if not snapshot.exists:
        raise HTTPException(
            status_code=404,
            detail="User profile not found. Please call /auth/register first.",
        )

    data = snapshot.to_dict()
    return UserProfile(
        uid=data["uid"],
        email=data.get("email", current_user.get("email", "")),
        display_name=data.get("display_name"),
        preferred_lang=data.get("preferred_lang", "en"),
        created_at=data.get("created_at"),
    )


@router.patch("/users/me", response_model=UserProfile)
async def update_me(
    body: UpdateUserRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update the authenticated user's display name and/or preferred language."""
    uid = current_user["uid"]
    user_ref = db.collection("users").document(uid)
    snapshot = await user_ref.get()

    if not snapshot.exists:
        raise HTTPException(
            status_code=404,
            detail="User profile not found. Please call /auth/register first.",
        )

    now = _utcnow()
    update_fields: dict = {"updated_at": now}
    if body.display_name is not None:
        update_fields["display_name"] = body.display_name
    if body.preferred_lang is not None:
        update_fields["preferred_lang"] = body.preferred_lang

    await user_ref.update(update_fields)
    data = {**snapshot.to_dict(), **update_fields}

    return UserProfile(
        uid=data["uid"],
        email=data.get("email", current_user.get("email", "")),
        display_name=data.get("display_name"),
        preferred_lang=data.get("preferred_lang", "en"),
        created_at=data.get("created_at"),
    )


@router.delete("/users/me", status_code=204)
async def delete_me(current_user: dict = Depends(get_current_user)):
    """Soft-delete the authenticated user's account by setting a deleted_at timestamp."""
    uid = current_user["uid"]
    user_ref = db.collection("users").document(uid)
    snapshot = await user_ref.get()

    if not snapshot.exists:
        raise HTTPException(status_code=404, detail="User profile not found.")

    await user_ref.update({"deleted_at": _utcnow()})
    return Response(status_code=204)
