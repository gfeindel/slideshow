# Slideshow

Build narrated HD instruction videos from a JSON config file. Each scene pairs a screenshot with narration text; ElevenLabs synthesizes the audio and FFmpeg assembles the final MP4 with optional WebVTT subtitles.

## Requirements

- Python 3.10+
- `ffmpeg` and `ffprobe` on your PATH
- An [ElevenLabs](https://elevenlabs.io) API key with text-to-speech access.

## Installation

```bash
pip install -e .
pip install pyinstaller
```

## Test
Run unit tests:

```bash
pytest tests/
```

## Build
Create a standalone binary with pyinstaller:
`pyinstaller --onefile --name slideshow main.py`

## Usage

```bash
# Render a video
slideshow --config config.json

# Write output to a specific directory
slideshow --config config.json --output-dir ./out

# Validate config and environment without rendering
slideshow --config config.json --check
```

Or run directly:

```bash
python main.py --config config.json
```

## Config reference

```jsonc
{
  "output_basename": "my-video",   // stem for .mp4 and .vtt output files
  "delay": 2.0,                    // seconds of silence after each clip (default 2.0)
  "emit_vtt": true,                // emit WebVTT subtitle file (default true)
  "fps": 30,
  "resolution": { "width": 1920, "height": 1080 },

  "voice": {
    "api_key": "...",              // fallback: ELEVENLABS_API_KEY env var
    "voice_id": "...",             // fallback: ELEVENLABS_VOICE_ID env var
    "model_id": "eleven_multilingual_v2",
    "language": "en",
    "speed": 1.0,                  // 0.7–1.2
    "stability": 0.5,
    "similarity_boost": 0.75,
    "style": 0.0,
    "use_speaker_boost": true,
    "seed": 42,                    // pin for reproducible audio
    "output_format": "mp3_44100_128"
  },

  // Optional title slide (generated via Pillow)
  "intro": {
    "title": "How to Do X",
    "subtitle": "Step-by-step guide",
    "narration": "Welcome to this guide on how to do X.",
    "logo": "assets/logo.png",
    "background_color": [255, 255, 255],
    "title_color": [0, 0, 0],
    "subtitle_color": [30, 30, 30],
    "title_font_path": "Calibri Bold",
    "subtitle_font_path": "Calibri",
    // Size in pts
    "title_font_size": 30,
    "subtitle_font_size": 28
  },

  "scenes": [
    {
      "image": "screenshots/step1.png",
      "narration": "First, open the application."
    },
    {
      "image": "screenshots/step2.png",
      "narration": "Next, click the Settings button."
    }
  ]
}
```

`title_font_path` / `subtitle_font_path` / `font_path` accept either a `.ttf`/`.otf` file path or a Windows font display name (e.g. `"Calibri Bold"`); the latter is resolved via the registry.

## Output

- `<output_basename>.mp4` — the rendered video
- `<output_basename>.vtt` — WebVTT transcript (when `emit_vtt` is true)
- JSON metadata printed to stdout on success
