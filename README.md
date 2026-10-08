# Slideshow

Build narrated HD instruction videos from a JSON config file. Each scene pairs a screenshot with narration text; a text-to-speech provider ([ElevenLabs](https://elevenlabs.io) or [OpenAI](https://platform.openai.com)) synthesizes the audio, and FFmpeg assembles the final MP4 with optional WebVTT subtitles.

## Requirements

- Python 3.10+
- `ffmpeg` and `ffprobe` on your PATH
- An API key for one of the supported TTS providers:
  - **ElevenLabs** — an account with text-to-speech access
  - **OpenAI** — an account with access to the audio speech API

## Installation

```bash
pip install -e .            # installs both the elevenlabs and openai SDKs
pip install pyinstaller     # only needed to build a standalone binary
```

## Test
Install the dev extras, then run the unit tests:

```bash
pip install -e ".[dev]"
pytest tests/
```

The tests stub out the provider SDKs, so they make no API calls and need no keys.

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

`--check` validates the whole config, including provider-specific rules such as model names, speed range, and narration length, without calling the TTS API.

## Config reference

```jsonc
{
  "output_basename": "my-video",   // stem for .mp4 and .vtt output files
  "delay": 2.0,                    // seconds of silence after each clip (default 2.0)
  "emit_vtt": true,                // emit WebVTT subtitle file (default true)
  "fps": 30,
  "resolution": { "width": 1920, "height": 1080 },

  // Text-to-speech settings — see "Voice settings" below
  "voice": {
    "provider": "elevenlabs",      // "elevenlabs" (default) or "openai"
    "api_key": "...",
    "voice_id": "..."
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

## Voice settings

`voice.provider` selects the TTS service. It defaults to `"elevenlabs"`, so configs written before OpenAI support was added keep working unchanged.

### ElevenLabs

```jsonc
"voice": {
  "provider": "elevenlabs",
  "api_key": "...",                // fallback: ELEVENLABS_API_KEY env var
  "voice_id": "...",               // required; fallback: ELEVENLABS_VOICE_ID env var
  "model_id": "eleven_multilingual_v2",  // default
  "language": "en",                // default
  "speed": 1.0,                    // 0.7–1.2
  "stability": 0.5,                // 0.0–1.0
  "similarity_boost": 0.75,        // 0.0–1.0
  "style": 0.0,                    // 0.0–1.0
  "use_speaker_boost": true,
  "seed": 42,                      // pin for reproducible audio
  "output_format": "mp3_44100_128",  // default; "pcm_44100" skips ffmpeg transcoding
  "base_url": "..."                // optional: override the API base URL
}
```

### OpenAI

```jsonc
"voice": {
  "provider": "openai",
  "api_key": "...",                // fallback: OPENAI_API_KEY env var
  "voice_id": "coral",             // built-in voice name; fallback: OPENAI_TTS_VOICE env var, then "alloy"
  "model_id": "gpt-4o-mini-tts",   // default; see supported models below
  "instructions": "Speak in a calm, friendly instructor tone.",
  "speed": 1.0,                    // 0.24–4.0
  "output_format": "pcm",          // default; also mp3, opus, aac, flac, wav
  "base_url": "..."                // optional: proxy or compatible endpoint
}
```

- **Models:** `tts-1`, `tts-1-hd`, `gpt-4o-mini-tts`, `gpt-4o-mini-tts-2025-12-15`. Any other `model_id` is rejected. Pin the dated snapshot if you need the voice to stay the same across re-renders.
- **`instructions`** steers tone and delivery. Only the `gpt-4o-mini-tts` models support it; with `tts-1`/`tts-1-hd` it's ignored with a warning.
- **Narration length:** each narration (intro and every scene) must be 4096 characters or fewer.
- **Output:** the default `pcm` output is wrapped directly as a 24 kHz WAV. Other formats are transcoded with ffmpeg.
- **Consistency:** OpenAI has no equivalent of ElevenLabs' `seed` or request stitching, so use `instructions` to keep the voice consistent from scene to scene.

### Field support by provider

| Field | ElevenLabs | OpenAI |
|---|---|---|
| `provider` | ✓ | ✓ |
| `api_key` | ✓ | ✓ |
| `voice_id` | ✓ (required) | ✓ (default `alloy`) |
| `model_id` | ✓ | ✓ (validated) |
| `speed` | 0.7–1.2 | 0.24–4.0 |
| `output_format` | ✓ | ✓ |
| `base_url` | ✓ | ✓ |
| `language` | ✓ | — |
| `stability`, `similarity_boost`, `style`, `use_speaker_boost` | ✓ | — |
| `seed` | ✓ | — |
| `instructions` | — | ✓ (`gpt-4o-mini-tts` models) |

Fields that don't apply to the selected provider are ignored, and a warning is printed to stderr. `language` is the exception: OpenAI ignores it without a warning.

### Environment variables

| Variable | Used for |
|---|---|
| `ELEVENLABS_API_KEY` | ElevenLabs API key when `voice.api_key` is empty |
| `ELEVENLABS_VOICE_ID` | ElevenLabs voice when `voice.voice_id` is empty |
| `OPENAI_API_KEY` | OpenAI API key when `voice.api_key` is empty |
| `OPENAI_TTS_VOICE` | OpenAI voice when `voice.voice_id` is empty |

Prefer environment variables over putting API keys in config files.

## Output

- `<output_basename>.mp4` — the rendered video
- `<output_basename>.vtt` — WebVTT transcript (when `emit_vtt` is true)
- JSON metadata printed to stdout on success, including `tts_engine` (`"elevenlabs"` or `"openai"`). `--check` also reports `tts_model`.
- Warnings and errors are printed to stderr; errors exit with code 2.
