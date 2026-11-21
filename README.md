# 🏥 MedAI Assistant: Bilingual Medical Student AI Assistant

An end-to-end, production-ready, zero-cost-to-start Android application and backend service designed specifically for medical education with bilingual support (Tamil & English).

---

## 📁 Repository Structure

```
medai-assistant/
├── backend/                  # Python FastAPI Backend
│   ├── app/
│   │   ├── middleware/       # Sliding-window Rate Limiter (5 RPM, 25 RPD)
│   │   ├── routers/          # Auth, Conversations, and Messages Endpoints
│   │   ├── config.py         # Environment Settings
│   │   ├── dependencies.py   # Bearer Token Auth Guard
│   │   ├── firebase_client.py# Firebase Admin & Firestore Async Client
│   │   ├── gemini_client.py  # Gemini 1.5 Flash Prompt & JSON Schema Engine
│   │   ├── main.py           # FastAPI Application Entrypoint
│   │   └── schemas.py        # Pydantic v2 Request/Response Models
│   ├── Dockerfile            # Container configuration
│   ├── render.yaml           # One-click Render.com free deployment spec
│   ├── requirements.txt      # Python dependencies
│   ├── .env.example          # Sample environment variables
│   └── README.md             # Backend setup & deployment guide
│
└── android/                  # Native Android Application (Kotlin + Jetpack Compose)
    ├── app/
    │   ├── src/main/java/com/medai/assistant/
    │   │   ├── data/
    │   │   │   ├── api/      # Retrofit API interface & models
    │   │   │   └── repository/# Auth and Chat repositories
    │   │   ├── di/           # Hilt Dependency Injection modules
    │   │   ├── ui/
    │   │   │   ├── auth/     # Login, Register, Forgot Password screens
    │   │   │   ├── chat/     # Bilingual Chat screen with on-device TTS
    │   │   │   ├── history/  # Private Conversation History screen
    │   │   │   └── theme/    # Material 3 Medical Theme
    │   │   ├── MainActivity.kt
    │   │   └── MedAiApp.kt
    │   ├── build.gradle.kts  # App Gradle configuration
    │   └── AndroidManifest.xml
    ├── gradle/libs.versions.toml # Version catalog
    ├── build.gradle.kts      # Project-level Gradle
    ├── settings.gradle.kts
    └── README.md             # Android compilation & run guide
```

---

## ⚡ Key Highlights & Zero-Cost Architecture

1. **Zero Financial Cost to Start**:
   - **AI Brain**: Google Gemini 1.5 Flash (via free API key from Google AI Studio: 1,500 questions/day free).
   - **Database & Auth**: Google Firebase Auth + Cloud Firestore (50K reads/day, 20K writes/day free).
   - **Text-to-Speech (TTS)**: On-device Android `TextToSpeech` engine with native Tamil (`ta-IN`) and English (`en-US`) support (100% free, zero cloud API costs).
   - **Backend Hosting**: Render.com free tier (750 free web service hours/month).

2. **Medical Education Guardrails**:
   - Strictly confines discussions to medical topics (Anatomy, Physiology, Pharmacology, Clinical Medicine, etc.).
   - Explicit non-medical filter: politely rejects non-medical prompts in both English and Tamil.
   - Clinical safety warnings attached automatically if personal symptoms or diagnosis inquiries are detected.
   - Preserves English medical nomenclature inside Tamil explanations.

3. **Privacy & Security by Design**:
   - Chat histories strictly partitioned under each user's authenticated UID.
   - Zero API keys or secrets embedded within the Android app.
   - Automatic JWT token refresh handled by Firebase SDK and OkHttp interceptors.
