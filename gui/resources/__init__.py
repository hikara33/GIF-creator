import sys
from pathlib import Path

from gui.resources.palette import *
from gui.resources.theme import THEME_STYLESHEET as THEME_STYLESHEET


def resource_path(name: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent.parent))
    return base / "gui" / "resources" / name