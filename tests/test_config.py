from __future__ import annotations

import struct
import zlib
from pathlib import Path

import pytest

from video.config import (
    _parse_intro,
    _parse_voice,
    clamp,
    parse_project,
    read_json_source,
    sanitize_basename,
)
from video.models import SkillError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_png(path: Path) -> Path:
    """Write a minimal valid 1×1 white PNG so image-existence checks pass."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        payload = tag + data
        return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    idat = chunk(b"IDAT", zlib.compress(b"\x00\xFF\xFF\xFF"))
    iend = chunk(b"IEND", b"")
    path.write_bytes(sig + ihdr + idat + iend)
    return path


# ---------------------------------------------------------------------------
# sanitize_basename
# ---------------------------------------------------------------------------

def test_sanitize_basename_alphanumeric():
    assert sanitize_basename("my-video") == "my-video"


def test_sanitize_basename_spaces_become_hyphens():
    assert sanitize_basename("hello world") == "hello-world"


def test_sanitize_basename_special_chars_removed():
    result = sanitize_basename("foo/bar:baz")
    assert "/" not in result
    assert ":" not in result


def test_sanitize_basename_dots_and_underscores_preserved():
    assert sanitize_basename("v1.0_final") == "v1.0_final"


def test_sanitize_basename_empty_string():
    assert sanitize_basename("") == "instruction-video"


def test_sanitize_basename_only_special_chars():
    assert sanitize_basename("!!!@@@") == "instruction-video"


def test_sanitize_basename_leading_trailing_stripped():
    result = sanitize_basename("---video---")
    assert not result.startswith("-")
    assert not result.endswith("-")


# ---------------------------------------------------------------------------
# clamp
# ---------------------------------------------------------------------------

def test_clamp_midpoint():
    assert clamp(0.5, 0.0, 1.0, "f") == 0.5


def test_clamp_at_lower_bound():
    assert clamp(0.0, 0.0, 1.0, "f") == 0.0


def test_clamp_at_upper_bound():
    assert clamp(1.0, 0.0, 1.0, "f") == 1.0


def test_clamp_returns_float():
    assert isinstance(clamp(1, 0, 2, "f"), float)


def test_clamp_below_raises():
    with pytest.raises(SkillError, match="myfield"):
        clamp(-0.1, 0.0, 1.0, "myfield")


def test_clamp_above_raises():
    with pytest.raises(SkillError, match="myfield"):
        clamp(1.1, 0.0, 1.0, "myfield")


# ---------------------------------------------------------------------------
# read_json_source
# ---------------------------------------------------------------------------

def test_read_json_source_valid(tmp_path):
    f = tmp_path / "config.json"
    f.write_text('{"key": "value", "num": 42}', encoding="utf-8")
    result = read_json_source(f)
    assert result == {"key": "value", "num": 42}


def test_read_json_source_file_not_found(tmp_path):
    with pytest.raises(SkillError, match="not found"):
        read_json_source(tmp_path / "nonexistent.json")


def test_read_json_source_invalid_json(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("{bad json", encoding="utf-8")
    with pytest.raises(SkillError, match="Invalid JSON"):
        read_json_source(f)


# ---------------------------------------------------------------------------
# _parse_voice
# ---------------------------------------------------------------------------

def test_parse_voice_defaults():
    v = _parse_voice({})
    assert v.model_id == "eleven_multilingual_v2"
    assert v.language == "en"
    assert v.speed == 1.0
    assert v.output_format == "mp3_44100_128"
    assert v.api_key is None
    assert v.voice_id is None


def test_parse_voice_custom_fields():
    v = _parse_voice({"api_key": "k", "voice_id": "v", "speed": 0.8, "seed": 7})
    assert v.api_key == "k"
    assert v.voice_id == "v"
    assert v.speed == 0.8
    assert v.seed == 7


def test_parse_voice_speed_zero_raises():
    with pytest.raises(SkillError, match="speed"):
        _parse_voice({"speed": 0.0})


def test_parse_voice_negative_speed_raises():
    with pytest.raises(SkillError, match="speed"):
        _parse_voice({"speed": -1.0})


def test_parse_voice_stability_out_of_range_raises():
    with pytest.raises(SkillError, match="stability"):
        _parse_voice({"stability": 1.5})


def test_parse_voice_similarity_boost_out_of_range_raises():
    with pytest.raises(SkillError, match="similarity_boost"):
        _parse_voice({"similarity_boost": -0.1})


def test_parse_voice_style_out_of_range_raises():
    with pytest.raises(SkillError, match="style"):
        _parse_voice({"style": 2.0})


def test_parse_voice_stability_at_bounds_ok():
    v = _parse_voice({"stability": 0.0})
    assert v.stability == 0.0
    v2 = _parse_voice({"stability": 1.0})
    assert v2.stability == 1.0


# ---------------------------------------------------------------------------
# _parse_intro
# ---------------------------------------------------------------------------

def test_parse_intro_minimal():
    intro = _parse_intro({"title": "T", "subtitle": "S", "narration": "N"})
    assert intro.title == "T"
    assert intro.subtitle == "S"
    assert intro.narration == "N"
    assert intro.logo is None


def test_parse_intro_strips_whitespace():
    intro = _parse_intro({"title": "  My Title  ", "subtitle": " Sub ", "narration": " Narr "})
    assert intro.title == "My Title"
    assert intro.subtitle == "Sub"
    assert intro.narration == "Narr"


def test_parse_intro_missing_title_raises():
    with pytest.raises(SkillError, match="title"):
        _parse_intro({"subtitle": "S", "narration": "N"})


def test_parse_intro_empty_title_raises():
    with pytest.raises(SkillError, match="title"):
        _parse_intro({"title": "   ", "subtitle": "S", "narration": "N"})


def test_parse_intro_missing_subtitle_raises():
    with pytest.raises(SkillError, match="subtitle"):
        _parse_intro({"title": "T", "narration": "N"})


def test_parse_intro_missing_narration_raises():
    with pytest.raises(SkillError, match="narration"):
        _parse_intro({"title": "T", "subtitle": "S"})


def test_parse_intro_custom_colors():
    intro = _parse_intro({
        "title": "T", "subtitle": "S", "narration": "N",
        "background_color": [10, 20, 30],
        "title_color": [255, 0, 0],
        "subtitle_color": [0, 255, 0],
    })
    assert intro.background_color == (10, 20, 30)
    assert intro.title_color == (255, 0, 0)
    assert intro.subtitle_color == (0, 255, 0)


def test_parse_intro_invalid_color_length_raises():
    with pytest.raises(SkillError, match="background_color"):
        _parse_intro({"title": "T", "subtitle": "S", "narration": "N", "background_color": [255, 0]})


def test_parse_intro_non_list_color_raises():
    with pytest.raises(SkillError, match="title_color"):
        _parse_intro({"title": "T", "subtitle": "S", "narration": "N", "title_color": "red"})


def test_parse_intro_logo_not_found_raises(tmp_path):
    with pytest.raises(SkillError, match="logo"):
        _parse_intro({
            "title": "T", "subtitle": "S", "narration": "N",
            "logo": str(tmp_path / "missing.png"),
        })


def test_parse_intro_logo_valid(tmp_path):
    logo = _write_png(tmp_path / "logo.png")
    intro = _parse_intro({
        "title": "T", "subtitle": "S", "narration": "N",
        "logo": str(logo),
    })
    assert intro.logo is not None
    assert intro.logo.exists()


def test_parse_intro_font_path_as_file(tmp_path):
    font_file = tmp_path / "myfont.ttf"
    font_file.write_bytes(b"dummy")
    intro = _parse_intro({
        "title": "T", "subtitle": "S", "narration": "N",
        "font_path": str(font_file),
    })
    assert intro.font_path == font_file.resolve()


def test_parse_intro_font_size_zero_raises():
    with pytest.raises(SkillError, match="title_font_size"):
        _parse_intro({"title": "T", "subtitle": "S", "narration": "N", "title_font_size": 0})


def test_parse_intro_font_size_negative_raises():
    with pytest.raises(SkillError, match="subtitle_font_size"):
        _parse_intro({"title": "T", "subtitle": "S", "narration": "N", "subtitle_font_size": -5})


def test_parse_intro_font_sizes_valid():
    intro = _parse_intro({
        "title": "T", "subtitle": "S", "narration": "N",
        "title_font_size": 96,
        "subtitle_font_size": 48,
    })
    assert intro.title_font_size == 96
    assert intro.subtitle_font_size == 48


# ---------------------------------------------------------------------------
# parse_project (integration)
# ---------------------------------------------------------------------------

def test_parse_project_minimal_intro_only():
    raw = {"intro": {"title": "My Title", "subtitle": "Sub", "narration": "Welcome."}}
    project = parse_project(raw)
    assert project.output_basename == "instruction-video"
    assert project.width == 1920
    assert project.height == 1080
    assert project.fps == 30
    assert project.delay == 2.0
    assert project.emit_vtt is True
    assert project.intro is not None
    assert len(project.scenes) == 0


def test_parse_project_with_scenes(tmp_path):
    img = _write_png(tmp_path / "shot.png")
    raw = {
        "output_basename": "test-video",
        "scenes": [{"image": str(img), "narration": "Step one."}],
    }
    project = parse_project(raw)
    assert project.output_basename == "test-video"
    assert len(project.scenes) == 1
    assert project.scenes[0].narration == "Step one."
    assert project.scenes[0].image.exists()


def test_parse_project_multiple_scenes(tmp_path):
    img1 = _write_png(tmp_path / "s1.png")
    img2 = _write_png(tmp_path / "s2.png")
    raw = {
        "scenes": [
            {"image": str(img1), "narration": "First."},
            {"image": str(img2), "narration": "Second."},
        ]
    }
    project = parse_project(raw)
    assert len(project.scenes) == 2


def test_parse_project_custom_resolution(tmp_path):
    img = _write_png(tmp_path / "img.png")
    raw = {
        "resolution": {"width": 1280, "height": 720},
        "fps": 24,
        "scenes": [{"image": str(img), "narration": "Hi."}],
    }
    project = parse_project(raw)
    assert project.width == 1280
    assert project.height == 720
    assert project.fps == 24


def test_parse_project_emit_vtt_false(tmp_path):
    img = _write_png(tmp_path / "img.png")
    raw = {
        "emit_vtt": False,
        "scenes": [{"image": str(img), "narration": "Hi."}],
    }
    project = parse_project(raw)
    assert project.emit_vtt is False


def test_parse_project_custom_delay(tmp_path):
    img = _write_png(tmp_path / "img.png")
    raw = {
        "delay": 0.5,
        "scenes": [{"image": str(img), "narration": "Hi."}],
    }
    project = parse_project(raw)
    assert project.delay == 0.5


def test_parse_project_zero_delay_ok(tmp_path):
    img = _write_png(tmp_path / "img.png")
    raw = {"delay": 0.0, "scenes": [{"image": str(img), "narration": "Hi."}]}
    project = parse_project(raw)
    assert project.delay == 0.0


def test_parse_project_negative_delay_raises(tmp_path):
    img = _write_png(tmp_path / "img.png")
    raw = {"delay": -1.0, "scenes": [{"image": str(img), "narration": "Hi."}]}
    with pytest.raises(SkillError, match="delay"):
        parse_project(raw)


def test_parse_project_zero_fps_raises(tmp_path):
    img = _write_png(tmp_path / "img.png")
    raw = {"fps": 0, "scenes": [{"image": str(img), "narration": "Hi."}]}
    with pytest.raises(SkillError):
        parse_project(raw)


def test_parse_project_zero_width_raises(tmp_path):
    img = _write_png(tmp_path / "img.png")
    raw = {
        "resolution": {"width": 0, "height": 1080},
        "scenes": [{"image": str(img), "narration": "Hi."}],
    }
    with pytest.raises(SkillError):
        parse_project(raw)


def test_parse_project_no_scenes_no_intro_raises():
    with pytest.raises(SkillError, match="scenes"):
        parse_project({})


def test_parse_project_empty_scenes_no_intro_raises():
    with pytest.raises(SkillError, match="scenes"):
        parse_project({"scenes": []})


def test_parse_project_scene_missing_image_raises(tmp_path):
    raw = {"scenes": [{"narration": "Hi."}]}
    with pytest.raises(SkillError, match="image"):
        parse_project(raw)


def test_parse_project_scene_image_not_found_raises(tmp_path):
    raw = {"scenes": [{"image": str(tmp_path / "nope.png"), "narration": "Hi."}]}
    with pytest.raises(SkillError, match="not found"):
        parse_project(raw)


def test_parse_project_scene_missing_narration_raises(tmp_path):
    img = _write_png(tmp_path / "img.png")
    raw = {"scenes": [{"image": str(img)}]}
    with pytest.raises(SkillError, match="narration"):
        parse_project(raw)


def test_parse_project_scene_empty_narration_raises(tmp_path):
    img = _write_png(tmp_path / "img.png")
    raw = {"scenes": [{"image": str(img), "narration": "   "}]}
    with pytest.raises(SkillError, match="narration"):
        parse_project(raw)


def test_parse_project_non_dict_raises():
    with pytest.raises(SkillError, match="object"):
        parse_project([])  # type: ignore[arg-type]


def test_parse_project_sanitizes_basename(tmp_path):
    img = _write_png(tmp_path / "img.png")
    raw = {
        "output_basename": "My Video Name!",
        "scenes": [{"image": str(img), "narration": "Hi."}],
    }
    project = parse_project(raw)
    assert " " not in project.output_basename
    assert "!" not in project.output_basename
