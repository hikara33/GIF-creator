from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from core.median_cut import RGBColor

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


@dataclass
class LoadedImage:
    width: int
    height: int
    pixels_2d: list[list[RGBColor]]
    source_path: Path

    def flatten(self) -> list[RGBColor]:
        return [pixel for row in self.pixels_2d for pixel in row]


def read_image(path: str | Path) -> LoadedImage:
    image_path = Path(path)

    if not image_path.exists():
        raise FileNotFoundError(f"Файл не найден: {image_path}")

    if image_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(
            f"Неподдерживаемый формат файла '{image_path.suffix}'. "
            f"Поддерживаются: {supported}"
        )

    try:
        with Image.open(image_path) as pil_image:
            rgb_image = pil_image.convert("RGB")
            width, height = rgb_image.size
            raw_pixels = list(rgb_image.getdata())
    except Exception as error:
        raise ValueError(f"Не удалось прочитать изображение '{image_path}': {error}") from error

    pixels_2d = [
        raw_pixels[row_index * width : (row_index + 1) * width]
        for row_index in range(height)
    ]

    return LoadedImage(
        width=width,
        height=height,
        pixels_2d=pixels_2d,
        source_path=image_path,
    )


def read_image_sequence(paths: list[str | Path]) -> list[LoadedImage]:
    if not paths:
        raise ValueError("Список изображений пуст — нечего читать")

    loaded_images = [read_image(path) for path in paths]

    first = loaded_images[0]
    for image in loaded_images[1:]:
        if (image.width, image.height) != (first.width, first.height):
            raise ValueError(
                f"Размеры кадров не совпадают: '{first.source_path.name}' "
                f"({first.width}x{first.height}) и '{image.source_path.name}' "
                f"({image.width}x{image.height}). Все кадры анимации должны "
                f"быть одинакового размера."
            )

    return loaded_images