from __future__ import annotations

import ctypes
import re
from pathlib import Path
from typing import Any, Optional, Tuple

from .models import IntroConfig, SkillError, _WINDOWS_FONT_CANDIDATES


def _resolve_font_name(name: str) -> Optional[Path]:
    """Look up a font display name in the Windows registry and return its resolved path."""
    try:
        import winreg
    except ImportError:
        return None

    fonts_dir = Path("C:/Windows/Fonts")
    reg_key = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
    name_lower = name.strip().lower()

    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_key) as key:
            i = 0
            while True:
                try:
                    reg_name, reg_value, _ = winreg.EnumValue(key, i)
                    i += 1
                    # Registry names look like "Calibri Bold (TrueType)" — strip the suffix.
                    display = re.sub(r"\s*\(.*?\)\s*$", "", reg_name).strip().lower()
                    if display == name_lower:
                        font_file = Path(reg_value)
                        if not font_file.is_absolute():
                            font_file = fonts_dir / font_file
                        if font_file.exists():
                            return font_file
                except OSError:
                    break
    except OSError:
        pass

    return None

def _get_windows_dpi():
    """Get Windows DPI value"""
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # 2 = per-monitor DPI aware
    dpi = ctypes.windll.user32.GetDpiForSystem()
    return dpi

def _load_font(font_path: Optional[Path], size: int) -> Any:
    try:
        from PIL import ImageFont
    except ImportError:
        return None
    if font_path and font_path.exists():
        return ImageFont.truetype(str(font_path), size)
    for candidate in _WINDOWS_FONT_CANDIDATES:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def generate_title_slide(intro: IntroConfig, width: int, height: int, output_path: Path) -> None:
    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise SkillError(
            "Pillow is required for title slide generation. Install it with: pip install Pillow"
        ) from exc

    img = Image.new("RGB", (width, height), color=intro.background_color)
    draw = ImageDraw.Draw(img)

    dpi = _get_windows_dpi()
    # Convert from pts to pixels based on scaling factor.
    title_size = int(intro.title_font_size*dpi/72) if intro.title_font_size is not None else max(48, height // 11)
    subtitle_size = int(intro.subtitle_font_size*dpi/72) if intro.subtitle_font_size is not None else max(28, height // 20)
    title_font = _load_font(intro.title_font_path or intro.font_path, title_size)
    subtitle_font = _load_font(intro.subtitle_font_path or intro.font_path, subtitle_size)

    def text_size(text: str, font: Any) -> Tuple[int, int]:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    tw, th = text_size(intro.title, title_font)
    sw, sh = text_size(intro.subtitle, subtitle_font)
    gap = max(12, height // 60)
    block_h = th + gap + sh
    title_y = (height - block_h) // 2
    subtitle_y = title_y + th + gap

    draw.text(((width - tw) // 2, title_y), intro.title, font=title_font, fill=intro.title_color)
    draw.text(((width - sw) // 2, subtitle_y), intro.subtitle, font=subtitle_font, fill=intro.subtitle_color)

    if intro.logo and intro.logo.exists():
        logo = Image.open(intro.logo).convert("RGBA")
        max_logo_h = height // 6
        max_logo_w = width // 4
        logo.thumbnail((max_logo_w, max_logo_h), Image.LANCZOS)
        padding = max(24, width // 60)
        lx = width - logo.width - padding
        ly = height - logo.height - padding
        img.paste(logo, (lx, ly), logo)

    img.save(str(output_path), format="PNG")
