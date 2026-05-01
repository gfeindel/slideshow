from __future__ import annotations

import wave
from pathlib import Path
from unittest.mock import patch

import pytest

from video.ffmpeg import (
    ensure_ffmpeg_tools,
    seconds_to_vtt,
    wav_duration_seconds,
    write_vtt,
)
from video.models import SkillError


# ---------------------------------------------------------------------------
# seconds_to_vtt
# ---------------------------------------------------------------------------

def test_seconds_to_vtt_zero():
    assert seconds_to_vtt(0.0) == "00:00:00.000"


def test_seconds_to_vtt_whole_seconds():
    assert seconds_to_vtt(5.0) == "00:00:05.000"


def test_seconds_to_vtt_minutes():
    assert seconds_to_vtt(90.0) == "00:01:30.000"


def test_seconds_to_vtt_one_hour():
    assert seconds_to_vtt(3600.0) == "01:00:00.000"


def test_seconds_to_vtt_hours_minutes_seconds():
    assert seconds_to_vtt(3661.0) == "01:01:01.000"


def test_seconds_to_vtt_milliseconds():
    assert seconds_to_vtt(1.123) == "00:00:01.123"


def test_seconds_to_vtt_half_second():
    assert seconds_to_vtt(0.5) == "00:00:00.500"


def test_seconds_to_vtt_rounds_to_nearest_ms():
    # 1.9999 → 2000 ms → 00:00:02.000
    assert seconds_to_vtt(1.9999) == "00:00:02.000"


def test_seconds_to_vtt_large_value():
    # 2 hours 30 minutes 15.75 seconds
    t = 2 * 3600 + 30 * 60 + 15.75
    assert seconds_to_vtt(t) == "02:30:15.750"


# ---------------------------------------------------------------------------
# write_vtt
# ---------------------------------------------------------------------------

def test_write_vtt_header(tmp_path):
    out = tmp_path / "test.vtt"
    write_vtt([], out)
    content = out.read_text(encoding="utf-8")
    assert content.startswith("WEBVTT")


def test_write_vtt_single_entry(tmp_path):
    out = tmp_path / "test.vtt"
    write_vtt([(0.0, 5.0, "Hello world")], out)
    content = out.read_text(encoding="utf-8")
    assert "00:00:00.000 --> 00:00:05.000" in content
    assert "Hello world" in content
    assert "1\n" in content


def test_write_vtt_multiple_entries(tmp_path):
    entries = [
        (0.0, 5.0, "First caption"),
        (7.0, 12.5, "Second caption"),
        (14.0, 20.0, "Third caption"),
    ]
    out = tmp_path / "test.vtt"
    write_vtt(entries, out)
    content = out.read_text(encoding="utf-8")
    assert "First caption" in content
    assert "Second caption" in content
    assert "Third caption" in content
    assert "00:00:07.000 --> 00:00:12.500" in content
    assert "1\n" in content
    assert "2\n" in content
    assert "3\n" in content


def test_write_vtt_entry_order(tmp_path):
    entries = [(0.0, 2.0, "First entry text"), (3.0, 5.0, "Second entry text")]
    out = tmp_path / "order.vtt"
    write_vtt(entries, out)
    content = out.read_text(encoding="utf-8")
    pos_first = content.index("First entry text")
    pos_second = content.index("Second entry text")
    assert pos_first < pos_second


def test_write_vtt_utf8_encoding(tmp_path):
    out = tmp_path / "unicode.vtt"
    write_vtt([(0.0, 3.0, "Héllo wörld")], out)
    content = out.read_text(encoding="utf-8")
    assert "Héllo wörld" in content


def test_write_vtt_creates_file(tmp_path):
    out = tmp_path / "new.vtt"
    assert not out.exists()
    write_vtt([(0.0, 1.0, "x")], out)
    assert out.exists()


# ---------------------------------------------------------------------------
# wav_duration_seconds
# ---------------------------------------------------------------------------

def _make_wav(path: Path, sample_rate: int = 44100, num_frames: int = 44100) -> Path:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * num_frames)
    return path


def test_wav_duration_one_second(tmp_path):
    wav = _make_wav(tmp_path / "one.wav", sample_rate=44100, num_frames=44100)
    assert abs(wav_duration_seconds(wav) - 1.0) < 1e-6


def test_wav_duration_half_second(tmp_path):
    wav = _make_wav(tmp_path / "half.wav", sample_rate=44100, num_frames=22050)
    assert abs(wav_duration_seconds(wav) - 0.5) < 1e-6


def test_wav_duration_two_seconds(tmp_path):
    wav = _make_wav(tmp_path / "two.wav", sample_rate=22050, num_frames=44100)
    assert abs(wav_duration_seconds(wav) - 2.0) < 1e-6


def test_wav_duration_stereo(tmp_path):
    path = tmp_path / "stereo.wav"
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        wf.writeframes(b"\x00\x00\x00\x00" * 44100)
    assert abs(wav_duration_seconds(path) - 1.0) < 1e-6


# ---------------------------------------------------------------------------
# ensure_ffmpeg_tools
# ---------------------------------------------------------------------------

def test_ensure_ffmpeg_tools_both_present():
    with patch("video.ffmpeg.shutil.which", side_effect=lambda name: f"/usr/bin/{name}"):
        ffmpeg, ffprobe = ensure_ffmpeg_tools()
    assert ffmpeg == "/usr/bin/ffmpeg"
    assert ffprobe == "/usr/bin/ffprobe"


def test_ensure_ffmpeg_tools_ffmpeg_missing():
    def _which(name: str):
        return None if name == "ffmpeg" else f"/usr/bin/{name}"

    with patch("video.ffmpeg.shutil.which", side_effect=_which):
        with pytest.raises(SkillError, match="ffmpeg"):
            ensure_ffmpeg_tools()


def test_ensure_ffmpeg_tools_ffprobe_missing():
    def _which(name: str):
        return None if name == "ffprobe" else f"/usr/bin/{name}"

    with patch("video.ffmpeg.shutil.which", side_effect=_which):
        with pytest.raises(SkillError, match="ffmpeg"):
            ensure_ffmpeg_tools()


def test_ensure_ffmpeg_tools_both_missing():
    with patch("video.ffmpeg.shutil.which", return_value=None):
        with pytest.raises(SkillError):
            ensure_ffmpeg_tools()
