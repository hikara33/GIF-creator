"""
Модуль метрик качества квантизации изображения.

Используется для оценки потерь при замене исходных цветов пикселей
цветами из ограниченной палитры. Метрики нужны для сравнительного
анализа в отчёте: как меняется качество при palette_size = 256 / 128 / 64.

Все метрики реализованы без сторонних библиотек — только стандартная
математика Python.
"""

from __future__ import annotations

import math

from core.median_cut import RGBColor


def mean_squared_error(
    original: list[list[RGBColor]],
    quantized: list[list[RGBColor]],
) -> float:
    """
    Среднеквадратичная ошибка (MSE) между исходным и квантизированным
    изображением.

    Вычисляется как среднее по всем пикселям и каналам значение
    квадрата разности: MSE = (1 / 3N) * sum((R - R')^2 + (G - G')^2 + (B - B')^2)

    Чем меньше MSE, тем ближе квантизированное изображение к оригиналу.
    Значение 0 означает идеальное совпадение.

    Args:
        original: двумерный массив пикселей исходного изображения.
        quantized: двумерный массив пикселей после квантизации, той же
            размерности.

    Returns:
        Значение MSE в диапазоне [0, 65025.0] (макс. при полной инверсии).
    """
    height = len(original)
    width = len(original[0]) if height > 0 else 0
    total_pixels = height * width

    if total_pixels == 0:
        return 0.0

    squared_sum = 0.0
    for y in range(height):
        for x in range(width):
            for channel in range(3):
                diff = original[y][x][channel] - quantized[y][x][channel]
                squared_sum += diff * diff

    return squared_sum / (3 * total_pixels)


def peak_signal_to_noise_ratio(mse: float) -> float:
    """
    Пиковое отношение сигнала к шуму (PSNR) в децибелах.

    PSNR = 10 * log10(255^2 / MSE)

    Более интуитивная метрика чем MSE: значение выше 40 дБ считается
    хорошим качеством, выше 30 дБ — приемлемым.
    Возвращает float('inf') при MSE == 0 (изображения идентичны).

    Args:
        mse: значение MSE, полученное из mean_squared_error().
    """
    if mse == 0.0:
        return float("inf")

    return 10.0 * math.log10((255 ** 2) / mse)


def restore_quantized_image(
    indexed_pixels: list[list[int]],
    palette: list[RGBColor],
) -> list[list[RGBColor]]:
    """
    Восстанавливает изображение из индексов палитры обратно в RGB.

    Нужна для вычисления MSE/PSNR: после квантизации у нас есть
    индексы, но для сравнения с оригиналом нужны реальные RGB-цвета
    из палитры, которыми были заменены исходные пиксели.
    """
    return [
        [palette[index] for index in row]
        for row in indexed_pixels
    ]


def compare_quality(
    original_pixels: list[list[RGBColor]],
    indexed_pixels: list[list[int]],
    palette: list[RGBColor],
) -> dict[str, float]:
    """
    Вычисляет все метрики качества для одного кадра.

    Удобная функция-обёртка для вызова из GUI или отчётного кода.

    Returns:
        Словарь с ключами 'mse' и 'psnr'.
    """
    quantized = restore_quantized_image(indexed_pixels, palette)
    mse = mean_squared_error(original_pixels, quantized)
    psnr = peak_signal_to_noise_ratio(mse)

    return {"mse": round(mse, 4), "psnr": round(psnr, 2)}