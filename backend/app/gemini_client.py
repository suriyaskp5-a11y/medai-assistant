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
- Give detailed, informative answers like a knowledgeable assistant.
- Don't be vague. If asked "what is headache?", explain causes, types, symptoms, and remedies.
- For medical questions: add a brief note to consult a doctor for personal symptoms.
- For coding/tech questions: provide code examples when relevant.

## RESPONSE FORMAT
You MUST respond with ONLY valid JSON — no markdown code fences, no extra text before or after.
The JSON must conform exactly to this schema:

{
  "detected_input_language": "en" or "ta",
  "original_question": "<the question exactly as asked>",
  "english_question_translation": null,
  "english_answer": "<Detailed English answer using **bold** for headings and bullet points for structure>",
  "tamil_explanation": "<Detailed Tamil explanation preserving English technical terms in parentheses>",
  "key_medical_terms": [
    {"term": "<key term in English>", "tamil": "<Tamil meaning or transliteration>"}
  ],
  "safety_note": null,
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
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-flash-latest",
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
    parsed.setdefault("english_answer", "I'm here to help! Could you please ask your question again?")
    parsed.setdefault("tamil_explanation", "")
    parsed.setdefault("key_medical_terms", [])
    parsed.setdefault("safety_note", None)
    parsed.setdefault("sources", [])
    parsed.setdefault("out_of_scope", False)
    if not parsed.get("original_question"):
        parsed["original_question"] = question
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
    Call Pollinations.ai free text API (POST JSON with openai-fast model).
    This is completely free, needs NO API key, and has NO strict daily quota.
    """
    payload = {
        "messages": [
            {
                "role": "user",
                "content": f"{SYSTEM_PROMPT}\n\nQuestion: {question}\n\nRespond with ONLY valid JSON according to the schema."
            }
        ],
        "model": "openai-fast",
        "jsonMode": True
    }

    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.post(
            "https://text.pollinations.ai/",
            json=payload,
            headers={"Content-Type": "application/json", "User-Agent": "MedAI/1.0"}
        )
        response.raise_for_status()
        raw_text = response.text.strip()

    cleaned = _strip_code_fences(raw_text)

    # Extract JSON object from output
    json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if json_match:
        cleaned = json_match.group()

    parsed = json.loads(cleaned)
    return parsed


def _build_fallback_response(question: str) -> dict:
    """
    Build a helpful fallback response when all models are temporarily busy.
    """
    return {
        "detected_input_language": "en",
        "original_question": question,
        "english_question_translation": None,
        "english_answer": (
            f"**Your Question:** {question}\n\n"
            "The AI service is experiencing high traffic right now.\n\n"
            "• Please tap **Send** again in 10-15 seconds.\n"
            "• If this persists, the server will automatically reconnect shortly."
        ),
        "tamil_explanation": (
            f"**உங்கள் கேள்வி:** {question}\n\n"
            "AI சேவையில் தற்போது அதிகப்படியான பயன்பாடு உள்ளது.\n\n"
            "• தயவுசெய்து 10-15 வினாடிகள் கழித்து மீண்டும் **Send** அழுத்தவும்."
        ),
        "key_medical_terms": [],
        "safety_note": None,
        "sources": [],
        "out_of_scope": False,
    }


async def generate_medical_answer(question: str, conversation_history: list[dict]) -> dict:
    """
    Generate a bilingual answer for any question.
    1. Tries Gemini models.
    2. If Gemini hits quota limits (429 / ResourceExhausted), immediately uses Free Cloud LLM (Pollinations).
    3. If Gemini is unavailable, Free Cloud LLM answers seamlessly.
    4. Deterministic fallback message ensures no blank or unhandled crash.
    """
    gemini_quota_exhausted = False

    # 1. Try Gemini models
    for model_name in GEMINI_MODELS:
        if gemini_quota_exhausted:
            break
        try:
            logger.info(f"Attempting answer with Gemini model: {model_name}")
            parsed = await _call_gemini_model(model_name, question, conversation_history)
            logger.info(f"Successfully generated answer with {model_name}")
            return _sanitize_response(parsed, question)
        except Exception as e:
            err_str = str(e)
            logger.warning(f"Gemini {model_name} failed: {type(e).__name__} ({e})")
            # If 429 quota exhausted or rate limited, don't waste time trying other Gemini models with the same key
            if any(term in err_str for term in ["429", "ResourceExhausted", "RESOURCE_EXHAUSTED", "quota", "Quota"]):
                logger.warning("Gemini API quota exhausted (429). Switching immediately to Free Cloud LLM...")
                gemini_quota_exhausted = True
                break

    # 2. Free Cloud LLM (Unlimited, NO API key required, NO quota limit)
    try:
        logger.info("Attempting answer with Free Cloud LLM (Pollinations openai-fast)...")
        parsed = await _call_free_fallback_llm(question)
        logger.info("Successfully generated answer with Free Cloud LLM")
        return _sanitize_response(parsed, question)
    except Exception as e:
        logger.warning(f"Free Cloud LLM failed: {type(e).__name__} ({e})")

    # 3. Fallback message (Guaranteed to return valid schema)
    logger.info("Using built-in fallback response")
    return _build_fallback_response(question)
