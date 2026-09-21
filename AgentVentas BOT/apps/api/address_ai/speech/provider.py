from __future__ import annotations

from abc import ABC, abstractmethod

from address_ai.core.models import TranscriptionChunk


class SpeechProvider(ABC):
    @abstractmethod
    async def transcribe_audio(self, audio: bytes, *, language: str = "es-MX") -> list[TranscriptionChunk]:
        raise NotImplementedError

    async def transcribe_stream(self, chunks, *, language: str = "es-MX"):
        async for chunk in chunks:
            for item in await self.transcribe_audio(chunk, language=language):
                yield item


class DevelopmentSpeechProvider(SpeechProvider):
    async def transcribe_audio(self, audio: bytes, *, language: str = "es-MX") -> list[TranscriptionChunk]:
        text = audio.decode("utf-8", errors="ignore").strip()
        return [TranscriptionChunk(text=text, confidence=0.99, is_final=True)] if text else []
