"""
Модуль размытия в движении (Motion Blur) для кадров анимации.

Эффект достигается усреднением нескольких соседних кадров: каждый
пиксель результирующего кадра вычисляется как взвешенное среднее
значений того же пикселя в нескольких последовательных кадрах.

Это имитирует эффект реальной камеры, у которой затвор остаётся
открытым в течение нескольких кадров подряд — быстро движущиеся
объекты оставляют "след" и выглядят смазанными.

Алгоритм работает непосредственно с RGB-пикселями, до квантизации,
чтобы не вносить дополнительных артефактов.
"""

from __future__ import annotations

from core.median_cut import RGBColor


def _blend_pixels(
    pixel_stack: list[RGBColor],
    weights: list[float],
) -> RGBColor:
    """
    Смешивает несколько пикселей с заданными весами.

    Args:
        pixel_stack: список RGB-пикселей из соседних кадров.
        weights: веса каждого пикселя, должны суммироваться в 1.0.
    """
    r = sum(pixel[0] * w for pixel, w in zip(pixel_stack, weights))
    g = sum(pixel[1] * w for pixel, w in zip(pixel_stack, weights))
    b = sum(pixel[2] * w for pixel, w in zip(pixel_stack, weights))

    return (round(r), round(g), round(b))


def _build_linear_weights(count: int) -> list[float]:
    """
    Строит линейно убывающие веса: текущий кадр имеет наибольший вес,
    предыдущие — убывающий. Это даёт естественно выглядящий след.

    Например, для count=3: [0.5, 0.333, 0.167] (нормированные).
    """
    raw = [1.0 / (i + 1) for i in range(count)]
    total = sum(raw)
    return [w / total for w in raw]


def apply_motion_blur(
    frames: list[list[list[RGBColor]]],
    strength: int = 2,
) -> list[list[list[RGBColor]]]:
    """
    Применяет эффект motion blur ко всей последовательности кадров.

    Каждый выходной кадр — это взвешенное усреднение текущего кадра
    и (strength - 1) предыдущих. Для первых кадров, где предыдущих
    недостаточно, используются только доступные кадры.

    Args:
        frames: список кадров в формате pixels_2d[y][x] = (R, G, B).
        strength: количество кадров для смешивания (1 = без эффекта,
            2 = текущий + предыдущий, 3 = + ещё один и т.д.).
            Рекомендуемые значения: 2–4.

    Returns:
        Новый список кадров той же структуры с применённым эффектом.
        Исходные кадры не изменяются.
    """
    if strength < 1:
        raise ValueError("Параметр strength должен быть не меньше 1")

    if strength == 1 or not frames:
        return frames

    height = len(frames[0])
    width = len(frames[0][0]) if height > 0 else 0
    result: list[list[list[RGBColor]]] = []

    for frame_index in range(len(frames)):
        # Собираем окно из доступных предыдущих кадров + текущий
        window_start = max(0, frame_index - strength + 1)
        window = frames[window_start : frame_index + 1]

        # Для неполного окна (первые кадры) строим веса заново
        weights = _build_linear_weights(len(window))
        # Инвертируем: текущий кадр (последний в окне) должен иметь максимальный вес
        weights = list(reversed(weights))

        blurred_frame: list[list[RGBColor]] = []
        for y in range(height):
            row: list[RGBColor] = []
            for x in range(width):
                pixel_stack = [window[i][y][x] for i in range(len(window))]
                blended = _blend_pixels(pixel_stack, weights)
                row.append(blended)
            blurred_frame.append(row)

        result.append(blurred_frame)

    return result