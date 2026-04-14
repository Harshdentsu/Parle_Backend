import requests

from django.conf import settings

SARVAM_BASE_URL = "https://api.sarvam.ai"

LANGUAGE_TO_BCP47 = {
    "en": "en-IN",
    "hi": "hi-IN",
    "mr": "mr-IN",
    "bn": "bn-IN",
    "kn": "kn-IN",
    "ta": "ta-IN",
}


def _headers():
    return {
        "api-subscription-key": settings.SARVAM_API_KEY,
    }


def normalize_language_code(language_code):
    return LANGUAGE_TO_BCP47.get(language_code, "en-IN")


def safe_translate_to_english(text, source_language_code):
    try:
        return translate_to_english(text, source_language_code)
    except Exception as exc:
        print("Sarvam translate_to_english error:", str(exc))
        return text


def safe_translate_from_english(text, target_language_code):
    try:
        return translate_from_english(text, target_language_code)
    except Exception as exc:
        print("Sarvam translate_from_english error:", str(exc))
        return text


def safe_speech_to_english(audio_file):
    try:
        return speech_to_english(audio_file)
    except Exception as exc:
        print("Sarvam speech_to_english error:", str(exc))
        return {
            "transcript_english": "",
            "detected_language": None,
        }

def translate_to_english(text, source_language_code):
    if not text or source_language_code == "en":
        return text

    response = requests.post(
        f"{SARVAM_BASE_URL}/translate",
        headers={
            **_headers(),
            "Content-Type": "application/json",
        },
        json={
            "input": text,
            "source_language_code": normalize_language_code(source_language_code),
            "target_language_code": "en-IN",
            "speaker_gender": "Male",
            "mode": "formal",
            "model": "mayura:v1",
            "enable_preprocessing": True,
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("translated_text") or data.get("translation") or text


def translate_from_english(text, target_language_code):
    if not text or target_language_code == "en":
        return text

    response = requests.post(
        f"{SARVAM_BASE_URL}/translate",
        headers={
            **_headers(),
            "Content-Type": "application/json",
        },
        json={
            "input": text,
            "source_language_code": "en-IN",
            "target_language_code": normalize_language_code(target_language_code),
            "speaker_gender": "Male",
            "mode": "formal",
            "model": "mayura:v1",
            "enable_preprocessing": True,
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("translated_text") or data.get("translation") or text


def speech_to_english(audio_file):
    audio_file.seek(0)
    response = requests.post(
        f"{SARVAM_BASE_URL}/speech-to-text-translate",
        headers=_headers(),
        files={
            "file": (audio_file.name, audio_file, "application/octet-stream"),
        },
        data={
            "model": "saaras:v2.5",
        },
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    return {
        "transcript_english": data.get("transcript", "").strip(),
        "detected_language": data.get("language_code"),
    }
