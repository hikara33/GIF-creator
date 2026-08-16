from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from core.floyd_steinberg import apply_dithering
from core.gif_encoder import GifFrame, encode_gif
from core.lzw import _calculate_min_code_size, compress
from core.median_cut import build_palette, find_nearest_palette_indices

DEFAULT_PALETTE_SIZE = 256

if TYPE_CHECKING:
    from io_module.image_reader import LoadedImage

#колбэк прогресса
ProgressCallback = Callable[[int, int, str], None]


@dataclass
class GifBuildSettings:
    output_path: str | Path

    image_paths: list[str | Path] | None = None
    preloaded_frames: list | None = None

    palette_size: int = DEFAULT_PALETTE_SIZE
    frame_delay_centiseconds: int = 50  # 0.5 секунды по умолчанию
    per_frame_delays: list[int] | None = None
    loop_forever: bool = True

    #разный режим. без дизеринга - быстрее
    use_dithering: bool = True

    def __post_init__(self) -> None:
        if self.image_paths is None and self.preloaded_frames is None:
            raise ValueError(
                "Укажите image_paths или preloaded_frames - источник кадров обязателен"
            )
        if self.image_paths is not None and self.preloaded_frames is not None:
            raise ValueError(
                "Укажите только один источник: image_paths или preloaded_frames"
            )

    def delay_for_frame(self, index: int) -> int:
        if self.per_frame_delays is not None:
            return self.per_frame_delays[index]
        return self.frame_delay_centiseconds


def _report(callback: ProgressCallback | None, step: int, total: int, msg: str) -> None:
    if callback is not None:
        callback(step, total, msg)

def _load_frames(settings: GifBuildSettings) -> list[LoadedImage]:
    if settings.preloaded_frames is not None:
        return settings.preloaded_frames

    from io_module.image_reader import read_image_sequence
    return read_image_sequence(settings.image_paths)

def _quantize_frames(
        loaded_images: list[LoadedImage],
        palette: list,
        use_dithering: bool,
        callback: ProgressCallback | None,
        step: int,
        total: int,
) -> list[list[int]]:
    indexed_frames: list[list[int]] = []

    for i, image in enumerate(loaded_images):
        _report(callback, step, total, f"Квантизация кадра {i + 1}/{len(loaded_images)}")

        if use_dithering:
            indexed_2d = apply_dithering(image.pixels_2d, palette)
            indexed_flat = [idx for row in indexed_2d for idx in row]
        else:
            indexed_flat = find_nearest_palette_indices(image.flatten(), palette)

        indexed_frames.append(indexed_flat)

    return indexed_frames

def build_gif(
    settings: GifBuildSettings,
    progress_callback: ProgressCallback | None = None,
) -> bytes:
    total = 5

    #1. загрузка кадров
    _report(progress_callback, 1, total, "Загрузка кадров")
    loaded_images = _load_frames(settings)

    if not loaded_images:
        raise ValueError("Список кадров пуст")

    #2. единая палитра по всем кадрам
    _report(progress_callback, 2, total, "Построение цветовой палитры")
    all_pixels = [pixel for image in loaded_images for pixel in image.flatten()]
    palette = build_palette(all_pixels, palette_size=settings.palette_size)
    min_code_size = _calculate_min_code_size(len(palette))

    #3. квантизация
    model_label = "дизеринг" if settings.use_dithering else "быстрая квантизация"
    _report(progress_callback, 3, total, f"Квантизация кадров ({model_label})")
    indexed_frames = _quantize_frames(
        loaded_images, palette, settings.use_dithering,
        progress_callback, step=3, total=total,
    )

    #4. lzw сжатие
    _report(progress_callback, 4, total, "LZW-сжатие")
    compressed_frames = [
        compress(indices, palette_size=len(palette))
        for indices in indexed_frames
    ]

    #5. сборка GIF
    _report(progress_callback, 5, total, "Сборка GIF-файла")
    gif_frames = [
        GifFrame(
            width=loaded_images[i].width,
            height=loaded_images[i].height,
            indexed_pixels=indexed_frames[i],
            delay_centiseconds=settings.delay_for_frame(i),
        )
        for i in range(len(loaded_images))
    ]

    gif_bytes = encode_gif(
        gif_frames,
        palette,
        compressed_frames,
        min_code_size,
        settings.loop_forever,
    )

    output_path = Path(settings.output_path)
    output_path.write_bytes(gif_bytes)

    return gif_bytes
