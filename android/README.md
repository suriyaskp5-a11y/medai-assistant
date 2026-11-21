# MedAI Assistant Android Application (Kotlin + Jetpack Compose)

Production-ready native Android client for the MedAI Medical Student Assistant.

## 📱 Features
- **Modern Jetpack Compose & Material 3**: Adaptive medical-themed UI (Light & Dark modes)
- **Bilingual Chat (Tamil & English)**:
  - Automatic language detection
  - Shows English answer with clear headings and bullet points
  - Shows Tamil translation/meaning with English medical terminology preserved in parentheses
  - Key medical terms glossary cards
  - Verified medical citations & out-of-scope non-medical filtering
- **Dual Spoken Audio (English & Tamil)**:
  - Built-in on-device Android `TextToSpeech` engine (100% free, zero cloud TTS costs)
  - Separate controls to listen to English or Tamil explanations independently
- **Security & User Privacy**:
  - Firebase Authentication with email/password
  - All chat sessions strictly isolated per authenticated user
  - Automated Bearer token injection with OkHttp interceptor
  - Zero API keys or secrets inside the Android codebase

---

## 🚀 How to Open and Run

### 1. Prerequisites
- [Android Studio Iguana or newer](https://developer.android.com/studio)
- JDK 17+
- Android Device or Emulator running Android 8.0 (API level 26) or higher

### 2. Firebase Android Setup
1. In the [Firebase Console](https://console.firebase.google.com/), open your project.
2. Click **Add App > Android**:
   - Package name: `com.medai.assistant`
3. Download `google-services.json` and place it in:
   ```
   android/app/google-services.json
   ```
4. In Firebase Console, go to **Authentication > Sign-in method** and enable **Email/Password**.

### 3. Configure Backend URL
- In `android/app/build.gradle.kts`:
  - For Local Emulator: `http://10.0.2.2:8000/` (default)
  - For Physical Device: `http://<your-pc-lan-ip>:8000/`
  - For Production: `https://<your-app>.onrender.com/`

### 4. Build & Run
Open the `android/` directory in Android Studio, wait for Gradle sync, and click **Run (Shift + F10)**.

### 5. Enabling Tamil Voice on Android
For optimal Tamil speech output:
1. On your Android device, go to **Settings > System > Languages & input > Text-to-speech output**.
2. Select **Speech Services by Google** as the Preferred Engine.
3. Tap the Settings cog > **Install voice data > Tamil (India)**.
