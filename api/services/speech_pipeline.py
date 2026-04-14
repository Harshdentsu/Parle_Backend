import base64
import io

from django.conf import settings
from openai import OpenAI
from api.services.sarvam_language_service import (
    safe_speech_to_english,
    safe_translate_from_english,
    safe_translate_to_english,
)

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def _extension_from_mime(mime_type):
    mapping = {
        "audio/webm": "webm",
        "audio/webm;codecs=opus": "webm",
        "audio/ogg": "ogg",
        "audio/ogg;codecs=opus": "ogg",
        "audio/mp4": "mp4",
        "audio/mpeg": "mp3",
        "audio/mp3": "mp3",
        "audio/wav": "wav",
    }
    return mapping.get(mime_type, "webm")


def audio_base64_to_file(base64_audio, mime_type="audio/webm"):
    audio_bytes = base64.b64decode(base64_audio)
    audio_io = io.BytesIO(audio_bytes)
    extension = _extension_from_mime(mime_type)
    audio_io.name = f"audio.{extension}"
    audio_io.seek(0)
    return audio_io


def transcript_audio_to_english(base64_audio, source_language_code="en", mime_type="audio/webm"):
    if not base64_audio:
        return {
            "original_transcript": "",
            "english_transcript": "",
            "detected_language": source_language_code,
        }

    audio_file = audio_base64_to_file(base64_audio, mime_type=mime_type)

    sarvam_result = safe_speech_to_english(audio_file)
    english_transcript = (sarvam_result.get("transcript_english") or "").strip()
    detected_language = sarvam_result.get("detected_language") or source_language_code

    if english_transcript:
        return {
            "original_transcript": english_transcript,
            "english_transcript": english_transcript,
            "detected_language": detected_language,
        }

    audio_file.seek(0)
    original_transcript = speech_to_text(audio_file)
    english_transcript = safe_translate_to_english(original_transcript, source_language_code)

    return {
        "original_transcript": original_transcript,
        "english_transcript": english_transcript,
        "detected_language": detected_language or source_language_code,
    }


def normalize_user_query(user_query="", audio_base64=None, source_language_code="en", mime_type="audio/webm"):
    if audio_base64:
        transcript_data = transcript_audio_to_english(
            audio_base64,
            source_language_code=source_language_code,
            mime_type=mime_type,
        )
        return {
            "user_query_english": transcript_data["english_transcript"],
            "user_query_original": transcript_data["original_transcript"],
            "detected_language": transcript_data["detected_language"],
        }

    original_text = (user_query or "").strip()
    return {
        "user_query_original": original_text,
        "user_query_english": safe_translate_to_english(original_text, source_language_code),
        "detected_language": source_language_code,
    }


def localize_assistant_text(text, target_language_code="en", generate_audio=False):
    localized_text = safe_translate_from_english(text, target_language_code)
    audio_base64 = text_to_speech(localized_text) if generate_audio and localized_text else None
    return {
        "text": localized_text,
        "audio_base64": audio_base64,
    }

def speech_to_text(audio_file):
    try:
        audio_file.seek(0)
        transcription = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=audio_file
        )
        return transcription.text.strip()
    except Exception as e:
        print("Speech-to-Text Error:", str(e))
        return ""


def text_to_speech(text):
    try:
        response = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=text
        )
        return base64.b64encode(response.content).decode("utf-8")
    except Exception as e:
        print("Text-to-Speech Error:", str(e))
        return None
