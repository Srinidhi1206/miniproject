"""Audio analysis interfaces (Phase 2).

Planned pipeline: validate -> speech-to-text -> TextScamDetector, plus a
separate VoiceAuthenticityAnalyzer for synthetic-voice detection.

Neither engine ships in the MVP configuration. They are defined as
interfaces so they can be plugged in later, and the API reports them as
unavailable — SENTINEL never returns a fabricated audio or deepfake verdict.
"""

from __future__ import annotations

from typing import Protocol

from app.core.errors import SentinelError


class SpeechToText(Protocol):
    name: str

    def transcribe(self, audio: bytes, mime: str) -> str: ...


class VoiceAuthenticityAnalyzer(Protocol):
    name: str

    def score(self, audio: bytes, mime: str) -> float: ...


def get_transcriber() -> SpeechToText | None:
    return None  # e.g. faster-whisper, wired in Phase 2


def get_voice_authenticity() -> VoiceAuthenticityAnalyzer | None:
    return None


def audio_unavailable() -> SentinelError:
    return SentinelError(
        "CAPABILITY_UNAVAILABLE",
        "Voice analysis isn't available in the current configuration.",
        501,
        hint="Voice authenticity (deepfake) analysis is also unavailable. If you have a transcript of the call, "
             "paste it into the Message scanner instead.",
    )
