# StudentMate AI - Updated

## What changed
- Real AI chat backend via OpenAI Responses API.
- Bangla Unicode + English conversation.
- Conversation context in the current chat.
- Image upload for AI image understanding.
- Image generation and image-edit endpoints.
- Student-friendly AI interface with New Chat, image tools, copy button and suggestions.
- Study timer keeps the default 25 minutes and adds 45, 50, 60, 90, 120 minute presets plus custom minutes.
- Task page now shows completion progress and a clear step-by-step completion guide.
- Refreshed student-friendly backgrounds and cards.

## Run locally

1. Install Python 3.11+.
2. Open a terminal in this folder.
3. Run:
   `pip install -r requirements.txt`
4. Copy `.env.example` to `.env`.
5. Put your real OpenAI API key in `.env`:
   `OPENAI_API_KEY=...`
6. Run:
   `python app.py`
7. Open `http://127.0.0.1:5000`

Never put the API key in HTML/JavaScript or publish it to GitHub.

The AI uses the OpenAI Responses API. Image generation/editing requires access to the configured image model and normal API billing/limits.

## Included in this corrected build
- Dark mode now applies readable dark surfaces to Settings, Tasks, AI controls, calculator, cards, fields and task rows.
- Added a scientific calculator at `/calculator`, linked from Home/Study/Tasks.
- AI image picker now accepts standard mobile image types and reports upload/request errors instead of silently failing.
- Gemini default text/multimodal model updated to `gemini-3.7-flash`; OpenAI remains configurable through `STUDENTMATE_AI_MODEL`.

### Android WebView image upload
If this Flask app is wrapped inside an Android `WebView`, native file selection also requires the Android activity to implement `WebChromeClient.onShowFileChooser` and request the appropriate runtime camera permission when using camera capture. The web ZIP cannot control that Android-native file chooser layer.

For the Android WebView wrapper used for the APK, the corrected native file chooser example is included at `android-wrapper/MainActivity.kt`. Copy that activity into the Android Studio wrapper project so the AI `+` image button can open the phone's image picker.
