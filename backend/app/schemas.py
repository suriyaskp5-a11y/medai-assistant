from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SendMessageRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class KeyMedicalTerm(BaseModel):
    term: str
    tamil: str


class MessageResponse(BaseModel):
    message_id: str
    conversation_id: str
    detected_input_language: str
    original_question: str
    english_question_translation: Optional[str] = None
    english_answer: str
    tamil_explanation: str
    key_medical_terms: list[KeyMedicalTerm]
    safety_note: Optional[str] = None
    sources: list[str]
    out_of_scope: bool
    created_at: datetime


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    last_message_preview: Optional[str] = None


class ConversationDetail(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[dict] = []


class UserProfile(BaseModel):
    uid: str
    email: str
    display_name: Optional[str] = None
    preferred_lang: str = "en"
    created_at: Optional[datetime] = None


class UpdateUserRequest(BaseModel):
    display_name: Optional[str] = None
    preferred_lang: Optional[str] = None


class CreateConversationRequest(BaseModel):
    title: Optional[str] = "New Conversation"
