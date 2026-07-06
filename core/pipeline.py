from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from core.floyd_steinberg import apply_dithering
from core.gif_encoder import GifFrame, encode_gif
from core.lzw import _calculate_min_code_size, compress
from core.median_cut import build_palette
from core.motion_blur import apply_motion_blur
from io_module.image_reader import read_image_sequence

DEFAULT_PALETTE_SIZE = 256
DEFAULT_MOTION_BLUR_STRENGTH = 2

#колбэк прогресса
ProgressCallback = Callable[[int, int, str], None]


@dataclass
class GifBuildSettings:
    image_paths: list[str | Path]
    palette_size: int = DEFAULT_PALETTE_SIZE
    frame_delay_centiseconds: int = 50  # 0.5 секунды по умолчанию
    per_frame_delays: list[int] | None = None
    loop_forever: bool = True
    motion_blur: bool = False 
    motion_blur_strength: int = DEFAULT_MOTION_BLUR_STRENGTH

    def delay_for_frame(self, index: int) -> int:
        if self.per_frame_delays is not None:
            return self.per_frame_delays[index]
        return self.frame_delay_centiseconds


def _report_progress(callback: ProgressCallback | None, step: int, total: int, message: str) -> None:
    if callback is not None:
        callback(step, total, message)


def build_gif(
    settings: GifBuildSettings,
    progress_callback: ProgressCallback | None = None,
) -> bytes:
    if settings.per_frame_delays is not None:
        if len(settings.per_frame_delays) != len(settings.image_paths):
            raise ValueError(
                "Количество значений per_frame_delays должно совпадать "
                "с количеством изображений"
            )

    total_steps = 5

    #чтение изображений
    _report_progress(progress_callback, 1, total_steps, "Чтение изображений")
    loaded_images = read_image_sequence(settings.image_paths)

    frames_2d = [image.pixels_2d for image in loaded_images]

    #построение единой палитры по всем кадрам
    _report_progress(progress_callback, 2, total_steps, "Построение цветовой палитры")
    all_pixels = [pixel for frame in frames_2d for row in frame for pixel in row]
    palette = build_palette(all_pixels, palette_size=settings.palette_size)
    min_code_size = _calculate_min_code_size(len(palette))

    #квантизация и дизеринг каждого кадра
    _report_progress(progress_callback, 3, total_steps, "Квантизация и дизеринг кадров")
    indexed_frames: list[list[int]] = []
    for frame in frames_2d:
        indexed_2d = apply_dithering(frame, palette)
        indexed_flat = [index for row in indexed_2d for index in row]
        indexed_frames.append(indexed_flat)

    #LZW-сжатие каждого кадра
    _report_progress(progress_callback, 4, total_steps, "Сжатие данных алгоритмом LZW")
    compressed_frames = [
        compress(indices, palette_size=len(palette)) for indices in indexed_frames
    ]

    #сборка итогового GIF-файла
    _report_progress(progress_callback, 5, total_steps, "Сборка GIF-файла")
    gif_frames = [
        GifFrame(
            width=loaded_images[i].width,
            height=loaded_images[i].height,
            indexed_pixels=indexed_frames[i],
            delay_centiseconds=settings.delay_for_frame(i),
        )
        for i in range(len(loaded_images))
    ]

    return encode_gif(
        frames=gif_frames,
        palette=palette,
        lzw_compressed_frames=compressed_frames,
        min_code_size=min_code_size,
        loop_forever=settings.loop_forever,
    )