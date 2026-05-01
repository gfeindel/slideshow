from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .models import (
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
from .title_slide import _resolve_font_name


def clamp(value: float, lower: float, upper: float, field_name: str) -> float:
    if value < lower or value > upper:
        raise SkillError(f"{field_name} must be between {lower} and {upper}.")
    return float(value)


def read_json_source(json_file: Path) -> Dict[str, Any]:
    try:
        return json.loads(json_file.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SkillError(f"JSON file not found: {json_file}") from exc
    except json.JSONDecodeError as exc:
        raise SkillError(f"Invalid JSON in {json_file}: {exc}") from exc


def sanitize_basename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-._")
    return cleaned or "instruction-video"


def _parse_voice(v: Dict[str, Any]) -> VoiceConfig:
    voice = VoiceConfig(
        api_key=v.get("api_key"),
        voice_id=v.get("voice_id"),
        model_id=str(v.get("model_id", DEFAULT_MODEL_ID)),
        language=str(v.get("language", DEFAULT_LANGUAGE)),
        speed=float(v.get("speed", DEFAULT_SPEED)),
        stability=v.get("stability"),
        similarity_boost=v.get("similarity_boost"),
        style=v.get("style"),
        use_speaker_boost=v.get("use_speaker_boost"),
        seed=int(v["seed"]) if v.get("seed") is not None else None,
        output_format=str(v.get("output_format", "mp3_44100_128")),
        base_url=v.get("base_url"),
    )
    if voice.speed <= 0:
        raise SkillError("voice.speed must be greater than 0.")
    for field_name, val in [
        ("voice.stability", voice.stability),
        ("voice.similarity_boost", voice.similarity_boost),
        ("voice.style", voice.style),
    ]:
        if val is not None:
            clamp(float(val), 0.0, 1.0, field_name)
    return voice


def _parse_intro(intro_raw: Dict[str, Any]) -> IntroConfig:
    title_val = intro_raw.get("title")
    subtitle_val = intro_raw.get("subtitle")
    narration_val = intro_raw.get("narration")
    if not isinstance(title_val, str) or not title_val.strip():
        raise SkillError("intro.title must be a non-empty string.")
    if not isinstance(subtitle_val, str) or not subtitle_val.strip():
        raise SkillError("intro.subtitle must be a non-empty string.")
    if not isinstance(narration_val, str) or not narration_val.strip():
        raise SkillError("intro.narration must be a non-empty string.")

    logo_path: Optional[Path] = None
    logo_val = intro_raw.get("logo")
    if logo_val:
        logo_path = Path(str(logo_val)).expanduser().resolve()
        if not logo_path.exists():
            raise SkillError(f"intro.logo not found: {logo_path}")

    def _parse_font_path(key: str) -> Optional[Path]:
        val = intro_raw.get(key)
        if not val:
            return None
        val_str = str(val)
        if val_str.lower().endswith((".ttf", ".otf")) or "/" in val_str or "\\" in val_str:
            return Path(val_str).expanduser().resolve()
        resolved = _resolve_font_name(val_str)
        if resolved:
            return resolved
        raise SkillError(
            f"intro.{key}: font '{val_str}' not found. "
            'Provide a .ttf/.otf path or a font display name (e.g. "Calibri Bold").'
        )

    def _parse_font_size(key: str) -> Optional[int]:
        val = intro_raw.get(key)
        if val is None:
            return None
        size = int(val)
        if size <= 0:
            raise SkillError(f"intro.{key} must be a positive integer.")
        return size

    def _parse_color(key: str, default: Tuple[int, int, int]) -> Tuple[int, int, int]:
        val = intro_raw.get(key)
        if val is None:
            return default
        if not (isinstance(val, list) and len(val) == 3):
            raise SkillError(f"intro.{key} must be a list of 3 integers [R, G, B].")
        return (int(val[0]), int(val[1]), int(val[2]))

    return IntroConfig(
        title=title_val.strip(),
        subtitle=subtitle_val.strip(),
        narration=narration_val.strip(),
        logo=logo_path,
        background_color=_parse_color("background_color", DEFAULT_BACKGROUND),
        title_color=_parse_color("title_color", DEFAULT_TITLE_COLOR),
        subtitle_color=_parse_color("subtitle_color", DEFAULT_SUBTITLE_COLOR),
        font_path=_parse_font_path("font_path"),
        title_font_path=_parse_font_path("title_font_path"),
        subtitle_font_path=_parse_font_path("subtitle_font_path"),
        title_font_size=_parse_font_size("title_font_size"),
        subtitle_font_size=_parse_font_size("subtitle_font_size"),
    )


def _parse_scenes(scenes_raw: List[Any]) -> List[Scene]:
    scenes: List[Scene] = []
    for index, item in enumerate(scenes_raw, start=1):
        if not isinstance(item, dict):
            raise SkillError(f"Scene {index} must be an object.")
        image_value = item.get("image")
        narration_value = item.get("narration")
        if not image_value or not isinstance(image_value, str):
            raise SkillError(f"Scene {index} is missing a string image path.")
        if not isinstance(narration_value, str) or not narration_value.strip():
            raise SkillError(f"Scene {index} is missing narration text.")
        image_path = Path(image_value).expanduser().resolve()
        if not image_path.exists():
            raise SkillError(f"Scene {index} image not found: {image_path}")
        scenes.append(Scene(image=image_path, narration=narration_value.strip()))
    return scenes


def parse_project(raw: Dict[str, Any]) -> ProjectConfig:
    if not isinstance(raw, dict):
        raise SkillError("Input JSON must be an object.")

    delay = float(raw.get("delay", DEFAULT_DELAY))
    if delay < 0:
        raise SkillError("delay must be 0 or greater.")

    output_basename = sanitize_basename(str(raw.get("output_basename", "instruction-video")))
    emit_vtt = bool(raw.get("emit_vtt", True))

    resolution = raw.get("resolution") or {}
    width = int(resolution.get("width", raw.get("width", DEFAULT_WIDTH)))
    height = int(resolution.get("height", raw.get("height", DEFAULT_HEIGHT)))
    fps = int(raw.get("fps", DEFAULT_FPS))
    if width <= 0 or height <= 0 or fps <= 0:
        raise SkillError("width, height, and fps must be positive integers.")

    voice = _parse_voice(raw.get("voice") or {})

    intro: Optional[IntroConfig] = None
    intro_raw = raw.get("intro")
    if intro_raw is not None:
        if not isinstance(intro_raw, dict):
            raise SkillError("intro must be an object.")
        intro = _parse_intro(intro_raw)

    scenes_raw = raw.get("scenes")
    if not intro and (not isinstance(scenes_raw, list) or not scenes_raw):
        raise SkillError("scenes must be a non-empty list (or provide an intro section).")
    if scenes_raw is not None and not isinstance(scenes_raw, list):
        raise SkillError("scenes must be a list.")

    return ProjectConfig(
        delay=delay,
        output_basename=output_basename,
        emit_vtt=emit_vtt,
        width=width,
        height=height,
        fps=fps,
        voice=voice,
        scenes=_parse_scenes(scenes_raw or []),
        intro=intro,
    )
