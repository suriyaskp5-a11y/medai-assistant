# MedAI Assistant Backend (FastAPI + Gemini + Firebase Firestore)

A production-ready, zero-cost-to-start backend service for the MedAI Medical Student Assistant bilingual (Tamil & English) Android application.

## 🚀 Zero-Cost Cloud Architecture
- **API Runtime**: FastAPI (Python 3.12)
- **AI Engine**: Google Gemini 1.5 Flash (via free API Studio key, 15 RPM / 1,500 RPD)
- **Authentication**: Firebase Authentication (ID Token verification via Firebase Admin SDK)
- **Database**: Cloud Firestore (NoSQL, Native Mode - 50K reads/day, 20K writes/day free)
- **Rate Limiting**: Sliding window in-memory limiter (5 req/min, 25 req/day per user)
- **Hosting Target**: Render.com Web Service (free tier, 750 free instance hours/month)

---

## 🛠️ Local Setup & Running

### 1. Prerequisites
- Python 3.12+ installed
- Free Gemini API key from [Google AI Studio](https://aistudio.google.com/)
- Free Firebase project with Firestore enabled in Native mode from [Firebase Console](https://console.firebase.google.com/)

### 2. Configure Environment
1. In Firebase Console: **Project Settings > Service accounts > Generate new private key**. Download the JSON file.
2. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
3. Set your environment variables in `.env`:
   - `GEMINI_API_KEY`: Your Gemini API key.
   - `FIREBASE_SERVICE_ACCOUNT_JSON`: The entire contents of your downloaded service account JSON file as a single-line string.

### 3. Install Dependencies & Run
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Visit API Documentation: `http://localhost:8000/docs`

---

## 🌐 Free Production Deployment (Render.com)

1. Push this directory to your GitHub repository.
2. Log in to [Render.com](https://render.com) and click **New > Web Service**.
3. Connect your repository.
4. Set:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. In **Environment Variables**, add:
   - `GEMINI_API_KEY`
   - `FIREBASE_SERVICE_ACCOUNT_JSON`
   - `ALLOWED_ORIGINS` = `*`
6. Click **Deploy Web Service**. Your public URL will be `https://<service-name>.onrender.com`.
