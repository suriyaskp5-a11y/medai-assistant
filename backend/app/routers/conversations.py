import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from google.cloud.firestore_v1 import AsyncDocumentReference

from app.dependencies import get_current_user
from app.firebase_client import db
from app.schemas import CreateConversationRequest, ConversationSummary, ConversationDetail

logger = logging.getLogger(__name__)

router = APIRouter()


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def _doc_to_summary(doc_id: str, data: dict, last_message_preview: str | None = None) -> ConversationSummary:
    return ConversationSummary(
        id=doc_id,
        title=data.get("title", "New Conversation"),
        created_at=data.get("created_at", _utcnow()),
        updated_at=data.get("updated_at", _utcnow()),
        last_message_preview=last_message_preview,
    )


@router.get("/conversations", response_model=list[ConversationSummary])
async def list_conversations(current_user: dict = Depends(get_current_user)):
    """List all conversations for the current user, ordered by most recent first."""
    uid = current_user["uid"]
    conv_ref = db.collection("users").document(uid).collection("conversations")
    query = conv_ref.order_by("updated_at", direction="DESCENDING").limit(50)

    summaries: list[ConversationSummary] = []
    async for doc in query.stream():
        data = doc.to_dict()
        # Fetch the most recent message for preview
        preview: str | None = None
        try:
            msg_query = (
                doc.reference.collection("messages")
                .order_by("created_at", direction="DESCENDING")
                .limit(1)
            )
            async for msg_doc in msg_query.stream():
                msg_data = msg_doc.to_dict()
                preview_text = msg_data.get("english_answer") or msg_data.get("text", "")
                preview = preview_text[:100] if preview_text else None
                break
        except Exception as e:
            logger.warning(f"Could not fetch preview for conversation {doc.id}: {e}")

        summaries.append(_doc_to_summary(doc.id, data, preview))

    return summaries


@router.post("/conversations", response_model=ConversationSummary, status_code=201)
async def create_conversation(
    body: CreateConversationRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a new conversation for the current user."""
    uid = current_user["uid"]
    now = _utcnow()
    conv_data = {
        "title": body.title or "New Conversation",
        "created_at": now,
        "updated_at": now,
    }
    conv_ref = db.collection("users").document(uid).collection("conversations")
    _ts, new_doc_ref = await conv_ref.add(conv_data)

    return ConversationSummary(
        id=new_doc_ref.id,
        title=conv_data["title"],
        created_at=now,
        updated_at=now,
        last_message_preview=None,
    )


@router.get("/conversations/{conv_id}", response_model=ConversationDetail)
async def get_conversation(
    conv_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get a conversation and its messages (latest 50)."""
    uid = current_user["uid"]
    conv_doc_ref = (
        db.collection("users").document(uid).collection("conversations").document(conv_id)
    )
    conv_snapshot = await conv_doc_ref.get()
    if not conv_snapshot.exists:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    data = conv_snapshot.to_dict()

    # Fetch messages ordered chronologically
    messages_list: list[dict] = []
    msg_query = (
        conv_doc_ref.collection("messages")
        .order_by("created_at")
        .limit(50)
    )
    async for msg_doc in msg_query.stream():
        msg_data = msg_doc.to_dict()
        msg_data["id"] = msg_doc.id
        # Convert datetime to ISO string for JSON serialisation
        for field in ("created_at",):
            if isinstance(msg_data.get(field), datetime):
                msg_data[field] = msg_data[field].isoformat()
        messages_list.append(msg_data)

    return ConversationDetail(
        id=conv_id,
        title=data.get("title", "New Conversation"),
        created_at=data.get("created_at", _utcnow()),
        updated_at=data.get("updated_at", _utcnow()),
        messages=messages_list,
    )


@router.delete("/conversations/{conv_id}", status_code=204)
async def delete_conversation(
    conv_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a conversation and all its messages."""
    uid = current_user["uid"]
    conv_doc_ref = (
        db.collection("users").document(uid).collection("conversations").document(conv_id)
    )
    conv_snapshot = await conv_doc_ref.get()
    if not conv_snapshot.exists:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    # Delete all messages in the subcollection first
    msg_collection = conv_doc_ref.collection("messages")
    async for msg_doc in msg_collection.stream():
        await msg_doc.reference.delete()

    # Delete the conversation document itself
    await conv_doc_ref.delete()

    return Response(status_code=204)
