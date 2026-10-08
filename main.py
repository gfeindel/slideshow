#!/usr/bin/env python3
"""Build a narrated HD instruction video from a JSON config file using ElevenLabs or OpenAI TTS.

Requires:
  pip install elevenlabs openai Pillow

Usage:
  python build-instruction-video.py --config config.json
  python build-instruction-video.py --config config.json --output-dir ./out
  python build-instruction-video.py --config config.json --check

JSON config reference
---------------------
Top-level fields:
  output_basename   Name stem for the generated .mp4 and .vtt files
  delay             Seconds of silence after each narration clip (default 2.0)
  emit_vtt          Emit a WebVTT transcript alongside the video (default true)
  fps               Frames per second (default 30)
  resolution        { "width": 1920, "height": 1080 }

voice object:
  provider          "elevenlabs" (default) or "openai"
  api_key           API key (fallback: ELEVENLABS_API_KEY / OPENAI_API_KEY env var)
  voice_id          ElevenLabs voice ID (fallback: ELEVENLABS_VOICE_ID env var), or
                    OpenAI voice name (fallback: OPENAI_TTS_VOICE env var, then "alloy")
  model_id          ElevenLabs default "eleven_multilingual_v2"; OpenAI default
                    "gpt-4o-mini-tts" (also tts-1, tts-1-hd, gpt-4o-mini-tts-2025-12-15)
  language          BCP-47 code, default "en" (ElevenLabs only)
  speed             ElevenLabs 0.7–1.2, OpenAI 0.24–4.0; default 1.0
  stability         0.0–1.0 (ElevenLabs only)
  similarity_boost  0.0–1.0 (ElevenLabs only)
  style             0.0–1.0 (ElevenLabs only)
  use_speaker_boost bool (ElevenLabs only)
  seed              integer — pin randomness for reproducible output (ElevenLabs only)
  instructions      Tone/style prompt (OpenAI gpt-4o-mini-tts models only)
  output_format     ElevenLabs default "mp3_44100_128" ("pcm_44100" skips ffmpeg);
                    OpenAI default "pcm" (also mp3, opus, aac, flac, wav)
  base_url          override the provider's API base URL

intro object (generates a title slide as the first scene):
  title             Large centered heading
  subtitle          Smaller text immediately below title
  narration         Narration text for the title slide
  logo              Path to logo image (placed in bottom-right corner)
  background_color  [R, G, B]  default [255, 255, 255]
  title_color       [R, G, B]  default [0, 0, 0]
  subtitle_color    [R, G, B]  default [30, 30, 30]
  font_path         Shared fallback font — .ttf/.otf path or display name (e.g. "Calibri Bold")
  title_font_path   Font for title only (overrides font_path); path or display name
  subtitle_font_path Font for subtitle only (overrides font_path); path or display name
  title_font_size   Integer pixel size for title (default: height / 11)
  subtitle_font_size Integer pixel size for subtitle (default: height / 20)

scenes list — each entry:
  image             Path to the screenshot/image file
  narration         Narration text for this scene
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from video.build import build_video
from video.config import parse_project, read_json_source
from video.ffmpeg import ensure_ffmpeg_tools
from video.models import SkillError
from video.tts import create_tts


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build an HD MP4 instruction video from a JSON config using ElevenLabs or OpenAI TTS."
    )
    parser.add_argument("--config", type=Path, required=True, help="Path to the JSON config file.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd(),
        help="Directory for generated files (default: current directory).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate config and environment, then exit without rendering.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    try:
        raw = read_json_source(args.config)
        project = parse_project(raw)
        ffmpeg, ffprobe = ensure_ffmpeg_tools()
        provider = create_tts(project.voice)

        if args.check:
            print(json.dumps({
                "ok": True,
                "message": "Config and environment look valid.",
                "tts_engine": provider.name,
                "tts_model": project.voice.model_id,
                "ffmpeg": ffmpeg,
                "ffprobe": ffprobe,
                "scene_count": len(project.scenes),
                "has_intro": project.intro is not None,
                "output_basename": project.output_basename,
                "resolution": f"{project.width}x{project.height}",
                "fps": project.fps,
            }, indent=2))
            return 0

        result = build_video(project, args.output_dir)
        print(json.dumps(result, indent=2))
        return 0

    except SkillError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
