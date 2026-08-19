from __future__ import annotations

from pathlib import Path


def load_theme() -> str:
    """Загружает QSS-тему из файла рядом с модулем."""
    css_path = Path(__file__).with_name("theme.qss")
    return css_path.read_text(encoding="utf-8")


THEME_STYLESHEET = load_theme()