from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple


DEFAULT_WIDTH = 1920
DEFAULT_HEIGHT = 1080
DEFAULT_FPS = 30
DEFAULT_DELAY = 2.0
DEFAULT_SPEED = 1.0
DEFAULT_BACKGROUND = (255, 255, 255)
DEFAULT_TITLE_COLOR = (0, 0, 0)
DEFAULT_SUBTITLE_COLOR = (30, 30, 30)
DEFAULT_MODEL_ID = "eleven_multilingual_v2"
DEFAULT_LANGUAGE = "en"

_WINDOWS_FONT_CANDIDATES = [
    "C:/Windows/Fonts/calibrib.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
]


class SkillError(Exception):
    pass


@dataclass
class VoiceConfig:
    api_key: Optional[str] = None
    voice_id: Optional[str] = None
    model_id: str = DEFAULT_MODEL_ID
    language: str = DEFAULT_LANGUAGE
    speed: float = DEFAULT_SPEED
    stability: Optional[float] = None
    similarity_boost: Optional[float] = None
    style: Optional[float] = None
    use_speaker_boost: Optional[bool] = None
    seed: Optional[int] = None
    output_format: str = "mp3_44100_128"
    base_url: Optional[str] = None


@dataclass
class Scene:
    image: Path
    narration: str


@dataclass
class IntroConfig:
    title: str
    subtitle: str
    narration: str
    logo: Optional[Path] = None
    background_color: Tuple[int, int, int] = field(default_factory=lambda: DEFAULT_BACKGROUND)
    title_color: Tuple[int, int, int] = field(default_factory=lambda: DEFAULT_TITLE_COLOR)
    subtitle_color: Tuple[int, int, int] = field(default_factory=lambda: DEFAULT_SUBTITLE_COLOR)
    font_path: Optional[Path] = None          # shared fallback font
    title_font_path: Optional[Path] = None    # overrides font_path for title
    subtitle_font_path: Optional[Path] = None # overrides font_path for subtitle
    title_font_size: Optional[int] = None     # None = auto (height / 11)
    subtitle_font_size: Optional[int] = None  # None = auto (height / 20)


@dataclass
class ProjectConfig:
    delay: float
    output_basename: str
    emit_vtt: bool
    width: int
    height: int
    fps: int
    voice: VoiceConfig
    scenes: List[Scene]
    intro: Optional[IntroConfig] = None
