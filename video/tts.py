from __future__ import annotations

import math
import os
import wave
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, Optional

from .ffmpeg import transcode_to_wav_from_bytes
from .models import SkillError, VoiceConfig


def _write_pcm_as_wav(pcm_bytes: bytes, sample_rate: int, wav_path: Path) -> None:
    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)


class ElevenLabsTTS:
    name = "elevenlabs"

    def __init__(self, voice: VoiceConfig) -> None:
        try:
            from elevenlabs.client import ElevenLabs
            from elevenlabs import VoiceSettings as _VoiceSettings
        except ImportError as exc:
            raise SkillError(
                "The 'elevenlabs' package is required. Install it with: pip install elevenlabs"
            ) from exc

        api_key = (voice.api_key or os.environ.get("ELEVENLABS_API_KEY", "")).strip()
        voice_id = (voice.voice_id or os.environ.get("ELEVENLABS_VOICE_ID", "")).strip()

        if not api_key:
            raise SkillError(
                "ElevenLabs requires an API key. "
                "Set voice.api_key or the ELEVENLABS_API_KEY environment variable."
            )
        if not voice_id:
            raise SkillError(
                "ElevenLabs requires a voice id. "
                "Set voice.voice_id or the ELEVENLABS_VOICE_ID environment variable."
            )

        self.voice_id = voice_id
        client_kwargs: Dict[str, Any] = {"api_key": api_key}
        if voice.base_url:
            client_kwargs["base_url"] = voice.base_url.rstrip("/")

        self._client = ElevenLabs(**client_kwargs)
        self._VoiceSettings = _VoiceSettings
        # Retain the last 3 request IDs so successive calls can use previous_request_ids
        # for voice consistency across the full narration sequence.
        self._request_ids: Deque[str] = deque(maxlen=3)

    def _build_voice_settings(self, voice: VoiceConfig) -> Optional[Any]:
        from .config import clamp
        kwargs: Dict[str, Any] = {}
        if voice.stability is not None:
            kwargs["stability"] = clamp(voice.stability, 0.0, 1.0, "voice.stability")
        if voice.similarity_boost is not None:
            kwargs["similarity_boost"] = clamp(
                voice.similarity_boost, 0.0, 1.0, "voice.similarity_boost"
            )
        if voice.style is not None:
            kwargs["style"] = clamp(voice.style, 0.0, 1.0, "voice.style")
        if voice.use_speaker_boost is not None:
            kwargs["use_speaker_boost"] = bool(voice.use_speaker_boost)
        if voice.speed and not math.isclose(voice.speed, 1.0, rel_tol=1e-6):
            kwargs["speed"] = clamp(voice.speed, 0.7, 1.2, "voice.speed")
        return self._VoiceSettings(**kwargs) if kwargs else None

    def synthesize(
        self,
        text: str,
        wav_path: Path,
        voice: VoiceConfig,
        previous_text: Optional[str] = None,
        next_text: Optional[str] = None,
    ) -> None:
        kwargs: Dict[str, Any] = {
            "voice_id": self.voice_id,
            "text": text,
            "model_id": voice.model_id,
            "output_format": voice.output_format,
        }
        if voice.language:
            kwargs["language_code"] = voice.language
        voice_settings = self._build_voice_settings(voice)
        if voice_settings is not None:
            kwargs["voice_settings"] = voice_settings
        if previous_text is not None:
            kwargs["previous_text"] = previous_text
        if next_text is not None:
            kwargs["next_text"] = next_text
        if voice.seed is not None:
            kwargs["seed"] = int(voice.seed)
        if self._request_ids:
            kwargs["previous_request_ids"] = list(self._request_ids)

        try:
            with self._client.text_to_speech.with_raw_response.convert(**kwargs) as raw:
                request_id = (
                    raw.headers.get("request-id") or raw.headers.get("x-request-id")
                )
                audio_bytes = b"".join(raw.data)
        except SkillError:
            raise
        except Exception as exc:
            raise SkillError(f"ElevenLabs synthesis failed: {exc}") from exc

        if request_id:
            self._request_ids.append(request_id)

        if not audio_bytes:
            raise SkillError("ElevenLabs returned an empty audio response.")

        fmt = voice.output_format
        if fmt.startswith("pcm_"):
            sample_rate = int(fmt.split("_")[1])
            _write_pcm_as_wav(audio_bytes, sample_rate, wav_path)
        elif fmt.startswith("wav_") or fmt == "wav":
            wav_path.write_bytes(audio_bytes)
        else:
            transcode_to_wav_from_bytes(audio_bytes, fmt, wav_path)

        if not wav_path.exists() or wav_path.stat().st_size == 0:
            raise SkillError("ElevenLabs reported success but produced no audio file.")
