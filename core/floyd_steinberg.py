"""
Модуль рассеивания ошибки квантизации методом Флойда-Стейнберга.

После квантизации палитры (см. median_cut.py) каждый пиксель
заменяется ближайшим цветом из ограниченной палитры (обычно 256
цветов). Разница между исходным и итоговым цветом — это "ошибка
квантизации". Без коррекции на изображении появляются резкие,
заметные глазу переходы между цветовыми зонами (банding).

Алгоритм Флойда-Стейнберга распределяет эту ошибку на ещё не
обработанные соседние пиксели по фиксированному шаблону весов:

                X    7/16
         3/16  5/16  1/16

где X — текущий пиксель. За счёт этого визуально кажется, что
изображение содержит больше оттенков, чем есть в палитре на самом
деле — глаз "усредняет" соседние пиксели.
"""

from __future__ import annotations

from core.median_cut import RGBColor, find_nearest_color_index

#шаблон распределения ошибки
_ERROR_DIFFUSION_PATTERN: tuple[tuple[int, int, float], ...] = (
    (1, 0, 7 / 16), # сосед справа
    (-1, 1, 3 / 16), # сосед снизу слева
    (0, 1, 5 / 16), # сосед сниза
    (1, 1, 1 / 16), # сосед сниза справа
)


def _clamp(value: float) -> int:
    return max(0, min(255, round(value)))


def _subtract_colors(a: RGBColor, b: RGBColor) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add_error(color: RGBColor, error: tuple[float, float, float], share: float) -> RGBColor:
    return (
        _clamp(color[0] + error[0] * share),
        _clamp(color[1] + error[1] * share),
        _clamp(color[2] + error[2] * share),
    )


def apply_dithering(
    pixels: list[list[RGBColor]],
    palette: list[RGBColor],
) -> list[list[int]]:
    """
    Квантизирует изображение с рассеиванием ошибки по Флойду-Стейнбергу.

    В отличие от простого индексирования (когда каждый пиксель
    независимо заменяется ближайшим цветом палитры), здесь ошибка
    округления накапливается и переносится на соседние пиксели,
    благодаря чему итоговое изображение визуально ближе к оригиналу.

    Args:
        pixels: двумерный массив цветов изображения, pixels[y][x] = (R, G, B).
        palette: палитра цветов, построенная функцией build_palette().

    Returns:
        Двумерный массив индексов в палитре той же размерности,
        что и pixels — это и есть данные, которые далее пойдут в LZW.
    """
    if not pixels or not pixels[0]:
        raise ValueError("Передано пустое изображение")

    height = len(pixels)
    width = len(pixels[0])

    working_buffer: list[list[RGBColor]] = [row[:] for row in pixels]
    indexed_result: list[list[int]] = [[0] * width for _ in range(height)]

    for y in range(height):
        for x in range(width):
            original_color = working_buffer[y][x]
            nearest_index = find_nearest_color_index(original_color, palette)
            palette_color = palette[nearest_index]

            indexed_result[y][x] = nearest_index

            error = _subtract_colors(original_color, palette_color)
            _distribute_error(working_buffer, x, y, width, height, error)

    return indexed_result


def _distribute_error(
    buffer: list[list[RGBColor]],
    x: int,
    y: int,
    width: int,
    height: int,
    error: tuple[float, float, float],
) -> None:
    for dx, dy, share in _ERROR_DIFFUSION_PATTERN:
        neighbor_x, neighbor_y = x + dx, y + dy

        if 0 <= neighbor_x < width and 0 <= neighbor_y < height:
            buffer[neighbor_y][neighbor_x] = _add_error(
                buffer[neighbor_y][neighbor_x], error, share
            )