import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from app.dependencies import get_current_user
from app.firebase_client import db
from app.gemini_client import generate_medical_answer
from app.schemas import KeyMedicalTerm, MessageResponse, SendMessageRequest

logger = logging.getLogger(__name__)

router = APIRouter()


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def _build_gemini_history(messages: list[dict]) -> list[dict]:
    """
    Convert Firestore message documents into the format expected by Gemini:
    [{"role": "user"|"model", "parts": [{"text": "..."}]}]
    """
    history = []
    for msg in messages:
        role = msg.get("role", "user")
        # Map Firestore roles to Gemini roles
        gemini_role = "model" if role == "assistant" else "user"

        # For assistant messages, use the english_answer as the representative text
        if role == "assistant":
            text = msg.get("english_answer", "")
        else:
            text = msg.get("text", "")

        if text:
            history.append({"role": gemini_role, "parts": [{"text": text}]})
    return history


@router.post(
    "/conversations/{conv_id}/messages",
    response_model=MessageResponse,
    status_code=201,
)
async def send_message(
    conv_id: str,
    body: SendMessageRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Send a message in a conversation and get an AI-generated medical education response.
    """
    uid = current_user["uid"]

    # 1. Verify the conversation exists and belongs to this user
    conv_ref = (
        db.collection("users").document(uid).collection("conversations").document(conv_id)
    )
    conv_snapshot = await conv_ref.get()
    if not conv_snapshot.exists:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    conv_data = conv_snapshot.to_dict()

    # 2. Validate text length (double-checked here as defence-in-depth)
    if len(body.text) > 2000:
        raise HTTPException(
            status_code=422, detail="Message text must not exceed 2000 characters."
        )

    # 3. Fetch last 10 messages for context (desc, then reverse for chronological order)
    msg_collection = conv_ref.collection("messages")
    recent_query = msg_collection.order_by("created_at", direction="DESCENDING").limit(10)
    recent_docs: list[dict] = []
    async for msg_doc in recent_query.stream():
        recent_docs.append(msg_doc.to_dict())
    # Reverse to get chronological order
    recent_docs.reverse()

    # 4. Build Gemini conversation history
    conversation_history = _build_gemini_history(recent_docs)

    # 5. Call Gemini
    ai_response = await generate_medical_answer(body.text, conversation_history)

    now = _utcnow()

    # 6. Save the user message to Firestore
    user_msg_data = {
        "role": "user",
        "text": body.text,
        "created_at": now,
    }
    _ts_u, user_msg_ref = await msg_collection.add(user_msg_data)

    # 7. Save the assistant (AI) message to Firestore
    assistant_msg_data = {
        "role": "assistant",
        "text": body.text,  # keep original question for reference
        "detected_input_language": ai_response.get("detected_input_language", "en"),
        "original_question": ai_response.get("original_question", body.text),
        "english_question_translation": ai_response.get("english_question_translation"),
        "english_answer": ai_response.get("english_answer", ""),
        "tamil_explanation": ai_response.get("tamil_explanation", ""),
        "key_medical_terms": ai_response.get("key_medical_terms", []),
        "safety_note": ai_response.get("safety_note"),
        "sources": ai_response.get("sources", []),
        "out_of_scope": ai_response.get("out_of_scope", False),
        "created_at": now,
    }
    _ts_a, assistant_msg_ref = await msg_collection.add(assistant_msg_data)

    # 8. Update the conversation's updated_at and auto-title if still default
    update_data: dict = {"updated_at": now}
    current_title = conv_data.get("title", "New Conversation")
    if current_title == "New Conversation":
        update_data["title"] = body.text[:60]
    await conv_ref.update(update_data)

    # 9. Build and return the MessageResponse
    raw_terms = ai_response.get("key_medical_terms", [])
    key_terms: list[KeyMedicalTerm] = []
    for t in raw_terms:
        if isinstance(t, dict) and "term" in t and "tamil" in t:
            key_terms.append(KeyMedicalTerm(term=t["term"], tamil=t["tamil"]))

    return MessageResponse(
        message_id=assistant_msg_ref.id,
        conversation_id=conv_id,
        detected_input_language=ai_response.get("detected_input_language", "en"),
        original_question=ai_response.get("original_question", body.text),
        english_question_translation=ai_response.get("english_question_translation"),
        english_answer=ai_response.get("english_answer", ""),
        tamil_explanation=ai_response.get("tamil_explanation", ""),
        key_medical_terms=key_terms,
        safety_note=ai_response.get("safety_note"),
        sources=ai_response.get("sources", []),
        out_of_scope=ai_response.get("out_of_scope", False),
        created_at=now,
    )


@router.get("/conversations/{conv_id}/messages")
async def list_messages(
    conv_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Return up to 50 messages in a conversation, ordered chronologically."""
    uid = current_user["uid"]

    # Verify conversation ownership
    conv_ref = (
        db.collection("users").document(uid).collection("conversations").document(conv_id)
    )
    conv_snapshot = await conv_ref.get()
    if not conv_snapshot.exists:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    messages: list[dict] = []
    msg_query = conv_ref.collection("messages").order_by("created_at").limit(50)
    async for msg_doc in msg_query.stream():
        msg_data = msg_doc.to_dict()
        msg_data["id"] = msg_doc.id
        # Serialise datetimes
        for field in ("created_at",):
            if isinstance(msg_data.get(field), datetime):
                msg_data[field] = msg_data[field].isoformat()
        messages.append(msg_data)

    return {"conversation_id": conv_id, "messages": messages, "count": len(messages)}
