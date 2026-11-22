import json
import logging
import re
from typing import Any

import google.generativeai as genai
import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Configure the Gemini SDK
try:
    genai.configure(api_key=settings.gemini_api_key)
except Exception as e:
    logger.warning(f"Could not configure Gemini SDK: {e}")

SYSTEM_PROMPT = """You are MedAI, a helpful bilingual AI assistant that answers ANY question clearly and comprehensively in both English and Tamil.

## YOUR ROLE
- Answer ANY question the user asks — medical, general knowledge, science, history, math, coding, advice, creative, etc.
- Do NOT refuse or restrict to medical topics only. Be like ChatGPT — helpful for everything.
- For medical/health questions, give detailed educational information.
- For general questions, give clear, complete, and informative answers.

## LANGUAGE RULES
- Detect whether the user's question is in Tamil or English.
- ALWAYS provide the english_answer in English with clear structure.
- Use **Bold text** for headings/important terms (wrap with double asterisks).
- Use numbered lists (1. 2. 3.) or bullet points (•) for lists.
- ALWAYS provide the tamil_explanation in Tamil script.
- Keep English technical terms in Tamil explanation — show the English term in parentheses.

## RESPONSE QUALITY
- Give detailed, informative answers like a knowledgeable friend.
- Don't be vague. If asked "what is headache?", explain causes, types, symptoms, and remedies.
- For medical questions: add a brief note to consult a doctor for personal symptoms.
- For coding/tech questions: provide actual code examples when relevant.

## RESPONSE FORMAT
You MUST respond with ONLY valid JSON — no markdown code fences, no extra text before or after.
The JSON must conform exactly to this schema:

{
  "detected_input_language": "en" or "ta",
  "original_question": "<the question exactly as asked>",
  "english_question_translation": "<English translation if original was Tamil, else null>",
  "english_answer": "<Detailed English answer using **bold** for headings and bullet points for structure>",
  "tamil_explanation": "<Tamil explanation preserving English technical terms in parentheses>",
  "key_medical_terms": [
    {"term": "<key term in English>", "tamil": "<Tamil meaning or transliteration>"}
  ],
  "safety_note": "<Brief note to consult a doctor if personal symptoms mentioned, else null>",
  "sources": [],
  "out_of_scope": false
}

IMPORTANT: out_of_scope must ALWAYS be false. Answer every question.
"""

_REQUIRED_FIELDS = {
    "detected_input_language",
    "original_question",
    "english_answer",
    "tamil_explanation",
    "key_medical_terms",
    "sources",
    "out_of_scope",
}

# Supported modern Gemini models in priority order
GEMINI_MODELS = [
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
]


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences that the model might add."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _sanitize_response(parsed: dict, question: str) -> dict:
    """Ensure all required fields exist in the response dictionary."""
    parsed.setdefault("detected_input_language", "en")
    parsed.setdefault("original_question", question)
    parsed.setdefault("english_question_translation", None)
    parsed.setdefault("english_answer", "I'm here to help! Could you please rephrase your question?")
    parsed.setdefault("tamil_explanation", "")
    parsed.setdefault("key_medical_terms", [])
    parsed.setdefault("safety_note", None)
    parsed.setdefault("sources", [])
    parsed.setdefault("out_of_scope", False)
    if not parsed.get("original_question"):
        parsed["original_question"] = question
    # Always set out_of_scope to False
    parsed["out_of_scope"] = False
    return parsed


async def _call_gemini_model(model_name: str, question: str, conversation_history: list[dict]) -> dict:
    """Call a specific Gemini model via the Google GenerativeAI SDK."""
    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=SYSTEM_PROMPT,
        generation_config=genai.GenerationConfig(
            temperature=0.7,
            max_output_tokens=2048,
            response_mime_type="application/json",
        ),
    )
    contents: list[dict[str, Any]] = list(conversation_history)
    contents.append({"role": "user", "parts": [{"text": question}]})

    response = await model.generate_content_async(contents)
    raw_text = response.text
    cleaned = _strip_code_fences(raw_text)
    parsed = json.loads(cleaned)

    if not _REQUIRED_FIELDS.issubset(set(parsed.keys())):
        missing = _REQUIRED_FIELDS - set(parsed.keys())
        raise ValueError(f"Response missing required fields: {missing}")

    return parsed


async def _call_free_fallback_llm(question: str) -> dict:
    """
    Call Pollinations.ai free text API as a fallback.
    Returns a parsed dict matching the required schema.
    """
    prompt = f"""{SYSTEM_PROMPT}

User question: {question}

Respond ONLY with valid JSON matching the schema above."""

    encoded_prompt = prompt.replace(" ", "%20").replace("\n", "%0A")
    # Use Pollinations text API
    url = f"https://text.pollinations.ai/{encoded_prompt}"

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        raw_text = response.text.strip()

    cleaned = _strip_code_fences(raw_text)

    # Try to find JSON in the response
    json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if json_match:
        cleaned = json_match.group()

    parsed = json.loads(cleaned)
    return parsed


def _build_fallback_response(question: str) -> dict:
    """
    Build a helpful fallback response when all AI models fail.
    """
    return {
        "detected_input_language": "en",
        "original_question": question,
        "english_question_translation": None,
        "english_answer": (
            f"**Your Question:** {question}\n\n"
            "I'm currently experiencing connectivity issues with the AI service. "
            "This usually happens when:\n"
            "• The AI service is temporarily overloaded\n"
            "• Network connectivity issues\n\n"
            "**Please try again in a moment** — the service should recover shortly.\n\n"
            "If you have a medical question, I recommend:\n"
            "• Consulting a qualified healthcare professional\n"
            "• Checking trusted medical resources like WebMD or Mayo Clinic"
        ),
        "tamil_explanation": (
            f"**உங்கள் கேள்வி:** {question}\n\n"
            "தற்போது AI சேவையில் இணைப்பு சிக்கல் உள்ளது. "
            "சிறிது நேரம் கழித்து மீண்டும் முயற்சிக்கவும்.\n\n"
            "மருத்துவ கேள்விகளுக்கு தகுதியான மருத்துவரை அணுகவும்."
        ),
        "key_medical_terms": [],
        "safety_note": None,
        "sources": [],
        "out_of_scope": False,
    }


async def generate_medical_answer(question: str, conversation_history: list[dict]) -> dict:
    """
    Generate a bilingual answer for any question.
    Tries modern Gemini models first; automatically falls back to Free Cloud LLM,
    and finally uses a helpful fallback message so requests never fail silently.
    """
    # 1. Try Gemini models
    for model_name in GEMINI_MODELS:
        try:
            logger.info(f"Attempting answer with Gemini model: {model_name}")
            parsed = await _call_gemini_model(model_name, question, conversation_history)
            logger.info(f"Successfully generated answer with {model_name}")
            return _sanitize_response(parsed, question)
        except Exception as e:
            logger.warning(f"Gemini {model_name} failed: {type(e).__name__} ({e}). Trying next...")

    # 2. Try Free Cloud LLM Fallback (No API key needed)
    try:
        logger.info("Attempting answer with Free Fallback LLM (Pollinations)...")
        parsed = await _call_free_fallback_llm(question)
        logger.info("Successfully generated answer with Free Fallback LLM")
        return _sanitize_response(parsed, question)
    except Exception as e:
        logger.warning(f"Free Fallback LLM failed: {type(e).__name__} ({e})")

    # 3. Helpful fallback message (Guaranteed to succeed)
    logger.info("Using built-in fallback response")
    return _build_fallback_response(question)
