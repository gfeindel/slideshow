from __future__ import annotations

from pathlib import Path

from video.models import (
    DEFAULT_BACKGROUND,
    DEFAULT_DELAY,
    DEFAULT_FPS,
    DEFAULT_HEIGHT,
    DEFAULT_LANGUAGE,
    DEFAULT_MODEL_ID,
    DEFAULT_SPEED,
    DEFAULT_SUBTITLE_COLOR,
    DEFAULT_TITLE_COLOR,
    DEFAULT_WIDTH,
    IntroConfig,
    ProjectConfig,
    Scene,
    SkillError,
    VoiceConfig,
)


def test_skill_error_is_exception():
    e = SkillError("oops")
    assert isinstance(e, Exception)
    assert str(e) == "oops"


def test_voice_config_defaults():
    v = VoiceConfig()
    assert v.model_id == DEFAULT_MODEL_ID
    assert v.language == DEFAULT_LANGUAGE
    assert v.speed == DEFAULT_SPEED
    assert v.output_format == "mp3_44100_128"
    assert v.api_key is None
    assert v.voice_id is None
    assert v.stability is None
    assert v.similarity_boost is None
    assert v.style is None
    assert v.use_speaker_boost is None
    assert v.seed is None
    assert v.base_url is None


def test_voice_config_custom():
    v = VoiceConfig(api_key="key", voice_id="vid", speed=0.9, seed=42)
    assert v.api_key == "key"
    assert v.voice_id == "vid"
    assert v.speed == 0.9
    assert v.seed == 42


def test_scene_construction():
    p = Path("/some/image.png")
    s = Scene(image=p, narration="Hello world")
    assert s.image == p
    assert s.narration == "Hello world"


def test_intro_config_defaults():
    intro = IntroConfig(title="T", subtitle="S", narration="N")
    assert intro.background_color == DEFAULT_BACKGROUND
    assert intro.title_color == DEFAULT_TITLE_COLOR
    assert intro.subtitle_color == DEFAULT_SUBTITLE_COLOR
    assert intro.logo is None
    assert intro.font_path is None
    assert intro.title_font_path is None
    assert intro.subtitle_font_path is None
    assert intro.title_font_size is None
    assert intro.subtitle_font_size is None


def test_intro_config_custom():
    intro = IntroConfig(
        title="My Title",
        subtitle="My Subtitle",
        narration="Welcome.",
        background_color=(10, 20, 30),
        title_font_size=96,
        subtitle_font_size=48,
    )
    assert intro.title == "My Title"
    assert intro.background_color == (10, 20, 30)
    assert intro.title_font_size == 96
    assert intro.subtitle_font_size == 48


def test_project_config_construction():
    voice = VoiceConfig()
    scene = Scene(image=Path("/img.png"), narration="text")
    project = ProjectConfig(
        delay=2.0,
        output_basename="test",
        emit_vtt=True,
        width=DEFAULT_WIDTH,
        height=DEFAULT_HEIGHT,
        fps=DEFAULT_FPS,
        voice=voice,
        scenes=[scene],
    )
    assert project.delay == 2.0
    assert project.output_basename == "test"
    assert project.emit_vtt is True
    assert project.width == DEFAULT_WIDTH
    assert project.height == DEFAULT_HEIGHT
    assert project.fps == DEFAULT_FPS
    assert project.intro is None
    assert len(project.scenes) == 1


def test_default_constants():
    assert DEFAULT_WIDTH == 1920
    assert DEFAULT_HEIGHT == 1080
    assert DEFAULT_FPS == 30
    assert DEFAULT_DELAY == 2.0
    assert DEFAULT_SPEED == 1.0
    assert DEFAULT_MODEL_ID == "eleven_multilingual_v2"
    assert DEFAULT_LANGUAGE == "en"
    assert DEFAULT_BACKGROUND == (255, 255, 255)
    assert DEFAULT_TITLE_COLOR == (0, 0, 0)
    assert DEFAULT_SUBTITLE_COLOR == (30, 30, 30)
