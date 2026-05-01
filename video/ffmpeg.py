from __future__ import annotations

import shlex
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import List, Tuple

from .models import SkillError


def run(cmd: List[str]) -> None:
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise SkillError(
            f"Command failed (exit {proc.returncode}): {' '.join(shlex.quote(x) for x in cmd)}\n"
            f"stderr:\n{proc.stderr.decode('utf-8', errors='replace')}"
        )


def ensure_ffmpeg_tools() -> Tuple[str, str]:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise SkillError("ffmpeg and ffprobe must be installed and available in PATH.")
    return ffmpeg, ffprobe


def transcode_to_wav_from_bytes(audio_bytes: bytes, source_format: str, wav_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SkillError(
            f"ffmpeg is required to transcode ElevenLabs output format {source_format!r} to WAV. "
            'Install ffmpeg or use voice.output_format="pcm_44100" to skip transcoding.'
        )
    ext = source_format.split("_", 1)[0] or "audio"
    with tempfile.NamedTemporaryFile(
        prefix="elevenlabs-", suffix=f".{ext}", delete=False
    ) as fh:
        tmp = Path(fh.name)
        fh.write(audio_bytes)
    try:
        run([ffmpeg, "-y", "-i", str(tmp), str(wav_path)])
    finally:
        tmp.unlink(missing_ok=True)


def wav_duration_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as fh:
        frames = fh.getnframes()
        rate = fh.getframerate()
        if rate <= 0:
            raise SkillError(f"Invalid WAV frame rate in {path}")
        return frames / float(rate)


def render_scene_segment(
    ffmpeg: str,
    image_path: Path,
    audio_path: Path,
    output_path: Path,
    width: int,
    height: int,
    fps: int,
    total_duration: float,
    delay: float,
) -> None:
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,format=yuv420p"
    )
    af = f"apad=pad_dur={delay:.3f},atrim=duration={total_duration:.3f}"
    run([
        ffmpeg, "-y",
        "-loop", "1", "-framerate", str(fps), "-i", str(image_path),
        "-i", str(audio_path),
        "-t", f"{total_duration:.3f}",
        "-vf", vf, "-af", af,
        "-r", str(fps),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-movflags", "+faststart",
        "-shortest",
        str(output_path),
    ])


def concat_segments(ffmpeg: str, concat_file: Path, output_path: Path) -> None:
    run([
        ffmpeg, "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c", "copy",
        str(output_path),
    ])


def seconds_to_vtt(seconds: float) -> str:
    total_ms = int(round(seconds * 1000.0))
    hours = total_ms // 3_600_000
    total_ms %= 3_600_000
    minutes = total_ms // 60_000
    total_ms %= 60_000
    secs = total_ms // 1000
    ms = total_ms % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"


def write_vtt(entries: List[Tuple[float, float, str]], output_path: Path) -> None:
    lines = ["WEBVTT", ""]
    for idx, (start, end, text) in enumerate(entries, start=1):
        lines.append(str(idx))
        lines.append(f"{seconds_to_vtt(start)} --> {seconds_to_vtt(end)}")
        lines.append(text)
        lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")
