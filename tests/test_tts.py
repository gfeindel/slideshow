from __future__ import annotations

import sys
import types
import wave

import pytest

from video.models import SkillError, VoiceConfig
from video.tts import ElevenLabsTTS, OpenAITTS, create_tts


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeSpeech:
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.calls = []
        self.clients = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return types.SimpleNamespace(content=self.content)


@pytest.fixture
def fake_openai(monkeypatch):
    """Install a stub 'openai' module and return the shared speech endpoint."""
    speech = _FakeSpeech(b"\x00\x00" * 2400)  # 0.1s of silence at 24 kHz

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.audio = types.SimpleNamespace(speech=speech)
            speech.clients.append(self)

    module = types.ModuleType("openai")
    module.OpenAI = FakeOpenAI
    monkeypatch.setitem(sys.modules, "openai", module)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_TTS_VOICE", raising=False)
    return speech


def _openai_voice(**kwargs) -> VoiceConfig:
    base = dict(provider="openai", api_key="k", model_id="gpt-4o-mini-tts", output_format="pcm")
    base.update(kwargs)
    return VoiceConfig(**base)


# ---------------------------------------------------------------------------
# OpenAITTS
# ---------------------------------------------------------------------------

def test_openai_missing_api_key_raises(fake_openai):
    with pytest.raises(SkillError, match="OPENAI_API_KEY"):
        OpenAITTS(_openai_voice(api_key=None))


def test_openai_api_key_from_env(fake_openai, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "env-key")
    OpenAITTS(_openai_voice(api_key=None))
    assert fake_openai.clients[0].kwargs["api_key"] == "env-key"


def test_openai_default_voice(fake_openai):
    assert OpenAITTS(_openai_voice()).voice_id == "alloy"


def test_openai_voice_from_env(fake_openai, monkeypatch):
    monkeypatch.setenv("OPENAI_TTS_VOICE", "coral")
    assert OpenAITTS(_openai_voice()).voice_id == "coral"


def test_openai_base_url_passed(fake_openai):
    OpenAITTS(_openai_voice(base_url="https://proxy.example/v1/"))
    assert fake_openai.clients[0].kwargs["base_url"] == "https://proxy.example/v1"


def test_openai_synthesize_request_minimal(fake_openai, tmp_path):
    voice = _openai_voice(voice_id="nova")
    OpenAITTS(voice).synthesize("Hello.", tmp_path / "out.wav", voice)
    assert fake_openai.calls == [{
        "model": "gpt-4o-mini-tts",
        "voice": "nova",
        "input": "Hello.",
        "response_format": "pcm",
    }]


def test_openai_synthesize_passes_speed_and_instructions(fake_openai, tmp_path):
    voice = _openai_voice(speed=1.5, instructions="Calm.")
    OpenAITTS(voice).synthesize("Hello.", tmp_path / "out.wav", voice)
    call = fake_openai.calls[0]
    assert call["speed"] == 1.5
    assert call["instructions"] == "Calm."


def test_openai_pcm_written_as_24khz_wav(fake_openai, tmp_path):
    voice = _openai_voice()
    out = tmp_path / "out.wav"
    OpenAITTS(voice).synthesize("Hello.", out, voice)
    with wave.open(str(out), "rb") as fh:
        assert fh.getframerate() == 24000
        assert fh.getnchannels() == 1
        assert fh.getsampwidth() == 2
        assert fh.getnframes() == 2400


def test_openai_empty_response_raises(fake_openai, tmp_path):
    fake_openai.content = b""
    voice = _openai_voice()
    with pytest.raises(SkillError, match="empty"):
        OpenAITTS(voice).synthesize("Hello.", tmp_path / "out.wav", voice)


def test_openai_api_error_wrapped(fake_openai, tmp_path):
    def boom(**kwargs):
        raise RuntimeError("rate limited")

    fake_openai.create = boom
    voice = _openai_voice()
    with pytest.raises(SkillError, match="OpenAI synthesis failed: rate limited"):
        OpenAITTS(voice).synthesize("Hello.", tmp_path / "out.wav", voice)


def test_openai_missing_package_raises(monkeypatch):
    monkeypatch.setitem(sys.modules, "openai", None)
    with pytest.raises(SkillError, match="pip install openai"):
        OpenAITTS(_openai_voice())


# ---------------------------------------------------------------------------
# create_tts
# ---------------------------------------------------------------------------

def test_create_tts_openai(fake_openai):
    assert isinstance(create_tts(_openai_voice()), OpenAITTS)


def test_create_tts_elevenlabs():
    pytest.importorskip("elevenlabs")
    voice = VoiceConfig(api_key="k", voice_id="v")
    assert isinstance(create_tts(voice), ElevenLabsTTS)


def test_create_tts_unknown_provider_raises():
    with pytest.raises(SkillError, match="provider"):
        create_tts(VoiceConfig(provider="polly"))
