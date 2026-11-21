import json
import logging
import re
from typing import Any

import google.generativeai as genai

from app.config import settings

logger = logging.getLogger(__name__)

# Configure the Gemini SDK
genai.configure(api_key=settings.gemini_api_key)

MEDICAL_SYSTEM_PROMPT = """You are MedEdu AI, a bilingual (Tamil/English) medical education assistant designed specifically for medical students in India.

## YOUR ROLE
You ONLY answer medical education questions covering:
- Anatomy & Histology
- Physiology
- Biochemistry
- Pathology & Pathophysiology
- Microbiology & Immunology
- Pharmacology & Therapeutics
- Community Medicine & Preventive Medicine
- Forensic Medicine
- Clinical subjects: Medicine, Surgery, Obstetrics & Gynaecology, Paediatrics, Ophthalmology, ENT, Psychiatry, Orthopaedics, Dermatology, Radiology

## LANGUAGE RULES
- Detect whether the user's question is in Tamil or English.
- ALWAYS provide the english_answer in English with clear headings and bullet points.
- ALWAYS provide the tamil_explanation in Tamil script. Keep English medical terms in Tamil explanation — show the English term in parentheses immediately after, e.g., "இதயம் (Heart) ஒரு தசை உறுப்பு (muscular organ) ஆகும்".
- If the question is in Tamil, still answer fully in both languages.

## OUT-OF-SCOPE RULES
- If the question is NOT about medical education (e.g., cooking, politics, sports, general knowledge, coding, math), set out_of_scope to true and return a polite refusal in both languages.
- If the user asks about their OWN symptoms or seeks personal medical advice or treatment decisions, include a safety_note reminding them to consult a licensed physician. Still answer the educational aspect if present.

## RESPONSE FORMAT
You MUST respond with ONLY valid JSON — no markdown code fences, no extra text before or after the JSON.
The JSON must conform exactly to this schema:

{
  "detected_input_language": "en" or "ta",
  "original_question": "<the question exactly as asked>",
  "english_question_translation": "<English translation if original was Tamil, else null>",
  "english_answer": "<Detailed English answer with ## headings and - bullet points for clarity>",
  "tamil_explanation": "<Tamil explanation preserving English medical terms in parentheses>",
  "key_medical_terms": [
    {"term": "<English medical term>", "tamil": "<Tamil translation or transliteration>"}
  ],
  "safety_note": "<Safety note if personal symptoms were mentioned, else null>",
  "sources": [],
  "out_of_scope": false
}

## QUALITY STANDARDS
- For out_of_scope questions: set out_of_scope to true, write a brief polite refusal in english_answer, and a Tamil refusal in tamil_explanation. All other fields can be empty strings or empty arrays.
- english_answer must use markdown-style headings (##) and bullet points (-) for readability on mobile.
- key_medical_terms should list 3–8 important terms from the answer.
- Never include patient-identifying information.
- Do not hallucinate references; keep sources as an empty array [].
"""

_ERROR_RESPONSE = {
    "detected_input_language": "en",
    "original_question": "",
    "english_question_translation": None,
    "english_answer": "Service temporarily unavailable. Please try again in a moment.",
    "tamil_explanation": "சேவை தற்காலிகமாக கிடைக்கவில்லை. சிறிது நேரம் கழித்து மீண்டும் முயற்சிக்கவும்.",
    "key_medical_terms": [],
    "safety_note": None,
    "sources": [],
    "out_of_scope": False,
}

_REQUIRED_FIELDS = {
    "detected_input_language",
    "original_question",
    "english_answer",
    "tamil_explanation",
    "key_medical_terms",
    "sources",
    "out_of_scope",
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=MEDICAL_SYSTEM_PROMPT,
    generation_config=genai.GenerationConfig(
        temperature=0.3,
        max_output_tokens=2048,
        response_mime_type="application/json",
    ),
)


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences that the model might add despite instructions."""
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ```
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


async def generate_medical_answer(question: str, conversation_history: list[dict]) -> dict:
    """
    Generate a medical education answer using Gemini 1.5 Flash.

    :param question: The user's latest question text.
    :param conversation_history: List of previous turns in Gemini content format.
    :return: Parsed JSON dict conforming to the medical answer schema.
    """
    try:
        # Build the contents list
        contents: list[dict[str, Any]] = list(conversation_history)
        contents.append({"role": "user", "parts": [{"text": question}]})

        response = await model.generate_content_async(contents)

        raw_text = response.text
        clean_text = _strip_code_fences(raw_text)

        parsed: dict = json.loads(clean_text)

        # Validate required fields exist
        missing = _REQUIRED_FIELDS - parsed.keys()
        if missing:
            logger.warning(f"Gemini response missing fields: {missing}")
            # Fill defaults for missing fields
            parsed.setdefault("detected_input_language", "en")
            parsed.setdefault("original_question", question)
            parsed.setdefault("english_question_translation", None)
            parsed.setdefault("english_answer", raw_text)
            parsed.setdefault("tamil_explanation", "")
            parsed.setdefault("key_medical_terms", [])
            parsed.setdefault("safety_note", None)
            parsed.setdefault("sources", [])
            parsed.setdefault("out_of_scope", False)

        # Ensure original_question is populated
        if not parsed.get("original_question"):
            parsed["original_question"] = question

        return parsed

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error from Gemini response: {e}")
        error = dict(_ERROR_RESPONSE)
        error["original_question"] = question
        return error
    except Exception as e:
        error_type = type(e).__name__
        logger.error(f"Gemini API error ({error_type}): {e}")
        error = dict(_ERROR_RESPONSE)
        error["original_question"] = question
        # Provide a slightly more specific message for rate limits
        if "quota" in str(e).lower() or "rate" in str(e).lower() or "429" in str(e):
            error["english_answer"] = (
                "AI service quota exceeded. Please wait a moment and try again."
            )
            error["tamil_explanation"] = (
                "AI சேவை வரம்பு தாண்டப்பட்டது. சிறிது நேரம் காத்து மீண்டும் முயற்சிக்கவும்."
            )
        return error
