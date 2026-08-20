from __future__ import annotations

from collections.abc import Callable
from functools import cache

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer

from gui.resources.palette import TEXT_SECONDARY

_VIEWBOX = 'viewBox="0 0 24 24"'

_STROKED = "stroke"
_FILLED = "fill"


def _upload() -> str:
    return (
        '<path d="M12 15V4m0 0l-4.5 4.5M12 4l4.5 4.5"/>'
        '<path d="M4 16.5V19a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2.5"/>'
    )


def _browse() -> str:
    return (
        '<path d="M4 7a2 2 0 0 1 2-2h3.2L11 7h7a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2'
        'H6a2 2 0 0 1-2-2z"/>'
    )


def _play_filled() -> str:
    return '<path d="M8.5 5.7v12.6L18.5 12z" fill="{c}" stroke="none"/>'


def _pause_filled() -> str:
    return (
        '<path d="M8.5 5.5h2.6v13H8.5zM12.9 5.5h2.6v13h-2.6z" fill="{c}" stroke="none"/>'
    )


def _restart() -> str:
    return '<path d="M20 12a8 8 0 1 1-2.34-5.66"/><path d="M20 3.5v5h-5"/>'


def _zoom_fit() -> str:
    return (
        '<circle cx="11" cy="11" r="6"/>'
        '<path d="M15.1 15.1L21 21"/>'
        '<path d="M4 9V6a2 2 0 0 1 2-2h3M20 9V6a2 2 0 0 0-2-2h-3"/>'
    )


def _download() -> str:
    return (
        '<path d="M12 3v11m0 0l-5-5m5 5l5-5"/>'
        '<path d="M5 19h14"/>'
    )


def _scissors() -> str:
    return (
        '<circle cx="6" cy="6.5" r="2.1"/>'
        '<circle cx="6" cy="17.5" r="2.1"/>'
        '<path d="M8.7 8.4L20 18M8.7 15.6L20 6"/>'
    )


def _start_marker() -> str:
    return '<path d="M7 5l10 7-10 7z" fill="{c}" stroke="none"/>'


def _end_marker() -> str:
    return (
        '<rect x="6" y="5" width="4.4" height="14" fill="{c}" stroke="none"/>'
        '<path d="M14.6 6.5v11M17.4 6.5v11"/>'
    )


def _loop() -> str:
    return (
        '<path d="M17 2l4 4-4 4"/>'
        '<path d="M3 11v-1a4 4 0 0 1 4-4h14"/>'
        '<path d="M7 22l-4-4 4-4"/>'
        '<path d="M21 13v1a4 4 0 0 1-4 4H3"/>'
    )


def _warning() -> str:
    return (
        '<path d="M12 4L21 18H3z"/>'
        '<path d="M12 10v4"/>'
        '<path d="M12 17v.01"/>'
    )


def _help() -> str:
    return (
        '<circle cx="12" cy="12" r="9"/>'
        '<path d="M9.5 9.2a2.6 2.6 0 0 1 5 .9c0 1.7-2.5 2.1-2.5 3.4"/>'
        '<path d="M12 16.6v.01"/>'
    )


def _minimize() -> str:
    return '<path d="M5 12h14"/>'


def _maximize() -> str:
    return '<rect x="6" y="6" width="12" height="12" rx="2"/>'


def _restore() -> str:
    return (
        '<rect x="6" y="9" width="9" height="9" rx="2"/>'
        '<path d="M9 6V5a1 1 0 0 1 1-1h8a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1h-1"/>'
    )


def _close() -> str:
    return '<path d="M6 6l12 12M18 6L6 18"/>'


#: Иконка -> функция, возвращающая SVG-тело (строкой, `{c}` = цвет штриха).
_ICONS: dict[str, Callable[[], str]] = {
    "upload": _upload,
    "browse": _browse,
    "play": _play_filled,
    "pause": _pause_filled,
    "restart": _restart,
    "zoom_fit": _zoom_fit,
    "download": _download,
    "scissors": _scissors,
    "start_marker": _start_marker,
    "end_marker": _end_marker,
    "loop": _loop,
    "warning": _warning,
    "help": _help,
    "minimize": _minimize,
    "maximize": _maximize,
    "restore": _restore,
    "close": _close,
}

ICON_NAMES = frozenset(_ICONS)


def _svg_source(name: str, color: str) -> bytes:
    body = _ICONS[name]().format(c=color)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" {_VIEWBOX} '
        f'fill="none" stroke="{color}" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    )
    return svg.encode("utf-8")


@cache
def _pixmap(name: str, color: str, size: int) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    renderer = QSvgRenderer(_svg_source(name, color))
    if renderer.isValid():
        painter = QPainter(pixmap)
        renderer.render(painter, QRectF(0, 0, size, size))
        painter.end()
    return pixmap


def icon(name: str, color: str = TEXT_SECONDARY, size: int = 20) -> QIcon:
    """Возвращает QIcon для указанной иконки.

    Аргs:
        name: ключ из ICON_NAMES.
        color: цвет штриха (обычно из gui.resources.palette).
        size: размер в пикселях.
    """
    if name not in _ICONS:
        raise ValueError(f"Неизвестная иконка: {name!r}. Доступно: {sorted(_ICONS)}")
    return QIcon(_pixmap(name, color, size))