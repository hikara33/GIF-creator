"""Доменные типы GUI: загружаемое медиа, пресеты качества, утилиты."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

#: Расширения, которые принимает интерфейс.
IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png"})
VIDEO_EXTENSIONS = frozenset({".mp4", ".mov", ".avi"})
ACCEPTED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS


class MediaKind(Enum):
    """Тип загруженных файлов: последовательность фото или одно видео."""

    IMAGES = "images"
    VIDEO = "video"


@dataclass(frozen=True)
class UploadedMedia:
    """Результат загрузки файлов в зону."""

    kind: MediaKind
    paths: tuple[Path, ...]

    @property
    def primary_path(self) -> Path:
        return self.paths[0]


@dataclass(frozen=True)
class QualityPreset:
    """Пресет качества -> размер палитры GIF."""

    label: str
    palette_size: int


QUALITY_PRESETS: tuple[QualityPreset, ...] = (
    QualityPreset("Low", 64),
    QualityPreset("Medium", 128),
    QualityPreset("High", 256),
)


def classify_files(paths: tuple[Path, ...]) -> UploadedMedia | None:
    """Классифицирует список файлов по типу медиа.

    Если все файлы — изображения одного размера геометрии, вернётся
    ``MediaKind.IMAGES``; если путь один и это видео — ``MediaKind.VIDEO``;
    иначе (несмешанный набор) — ``None``.
    """
    exts = {path.suffix.lower() for path in paths}

    if exts and exts <= IMAGE_EXTENSIONS:
        return UploadedMedia(MediaKind.IMAGES, paths)

    if len(paths) == 1 and exts <= VIDEO_EXTENSIONS:
        return UploadedMedia(MediaKind.VIDEO, paths)

    return None


def format_timecode(total_ms: int, /) -> str:
    """Форматирует миллисекунды как ``MM:SS.C``."""
    total_ms = max(0, int(total_ms))
    minutes, remainder = divmod(total_ms, 60_000)
    seconds, centis = divmod(remainder, 1000)
    centis = centis // 100
    return f"{minutes:02d}:{seconds:02d}.{centis}"


def clamp_delay_ms(value: int, min_ms: int = 20, max_ms: int = 2000) -> int:
    """Ограничивает задержку кадра допустимым диапазоном (мс)."""
    return max(min_ms, min(max_ms, int(value)))


def delay_for_speed(speed: float, base_delay_ms: int = 100) -> int:
    """Задержка кадра (мс) для заданного множителя скорости."""
    speed = max(0.1, float(speed))
    return clamp_delay_ms(round(base_delay_ms / speed))