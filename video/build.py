from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .ffmpeg import (
    concat_segments,
    ensure_ffmpeg_tools,
    render_scene_segment,
    wav_duration_seconds,
    write_vtt,
)
from .models import ProjectConfig, Scene, SkillError
from .title_slide import generate_title_slide
from .tts import ElevenLabsTTS


def build_video(project: ProjectConfig, output_dir: Path) -> Dict[str, Any]:
    ffmpeg, _ = ensure_ffmpeg_tools()
    provider = ElevenLabsTTS(project.voice)
    output_dir.mkdir(parents=True, exist_ok=True)

    video_path = output_dir / f"{project.output_basename}.mp4"
    vtt_path = output_dir / f"{project.output_basename}.vtt"

    with tempfile.TemporaryDirectory(prefix="video-instruction-builder-") as tmp:
        tmpdir = Path(tmp)

        # Build the full ordered scene list, intro first.
        all_scenes: List[Scene] = []
        if project.intro:
            print("Building title slide")
            title_image_path = tmpdir / "intro_title.png"
            generate_title_slide(project.intro, project.width, project.height, title_image_path)
            all_scenes.append(Scene(image=title_image_path, narration=project.intro.narration))
        all_scenes.extend(project.scenes)

        narrations = [s.narration for s in all_scenes]
        vtt_entries: List[Tuple[float, float, str]] = []
        current_time = 0.0
        segments: List[Path] = []

        for index, scene in enumerate(all_scenes, start=1):
            print(f"Scene {index}/{len(all_scenes)}: synthesizing narration")
            audio_path = tmpdir / f"scene_{index:03d}.wav"
            segment_path = tmpdir / f"scene_{index:03d}.mp4"

            provider.synthesize(
                text=scene.narration,
                wav_path=audio_path,
                voice=project.voice
                #previous_text=narrations[index - 2] if index > 1 else None,
                #next_text=narrations[index] if index < len(narrations) else None,
            )

            audio_duration = wav_duration_seconds(audio_path)
            if audio_duration <= 0:
                raise SkillError(f"Generated audio for scene {index} has zero duration.")

            total_duration = audio_duration + project.delay
            print(f"Scene {index}/{len(all_scenes)}: rendering segment")
            render_scene_segment(
                ffmpeg=ffmpeg,
                image_path=scene.image,
                audio_path=audio_path,
                output_path=segment_path,
                width=project.width,
                height=project.height,
                fps=project.fps,
                total_duration=total_duration,
                delay=project.delay,
            )
            segments.append(segment_path)
            vtt_entries.append((current_time, current_time + audio_duration, scene.narration))
            current_time += total_duration

        print("Concatenating segments")
        concat_path = tmpdir / "segments.txt"
        concat_path.write_text(
            "\n".join(f"file '{s.as_posix()}'" for s in segments) + "\n",
            encoding="utf-8",
        )
        concat_segments(ffmpeg, concat_path, video_path)

    if project.emit_vtt:
        write_vtt(vtt_entries, vtt_path)

    return {
        "video": str(video_path),
        "vtt": str(vtt_path) if project.emit_vtt else None,
        "tts_engine": provider.name,
        "scene_count": len(all_scenes),
        "resolution": f"{project.width}x{project.height}",
        "fps": project.fps,
    }
