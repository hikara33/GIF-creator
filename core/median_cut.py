"""
Модуль квантизации цветов методом медианного сечения (Median Cut).

Алгоритм строит палитру из заданного количества цветов на основе
анализа цветового распределения изображения. Реализованы два улучшения:

1. Взвешенное среднее при вычислении цвета сегмента — учитывается
   частота встречаемости каждого цвета, а не только уникальность.
2. Рекурсивное разбиение по каналу с максимальным диапазоном значений.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import IntEnum


class Channel(IntEnum):
    RED = 0
    GREEN = 1
    BLUE = 2


RGBColor = tuple[int, int, int]
WeightedColor = tuple[RGBColor, int]  # (цвет, количество вхождений)


@dataclass
class ColorBucket:
    """
    cегмент цветового пространства — группа цветов, которые
    в текущей итерации алгоритма считаются похожими
    """
    colors: list[WeightedColor]

    def __len__(self) -> int:
        return len(self.colors)

    def total_weight(self) -> int:
        return sum(weight for _, weight in self.colors)

    #разброс значений по одному каналу
    def channel_range(self, channel: Channel) -> int:
        values = [color[channel] for color, _ in self.colors]
        return max(values) - min(values)

    #ищем канал с этим же разбросом
    def widest_channel(self) -> Channel:
        ranges = {channel: self.channel_range(channel) for channel in Channel}
        return max(ranges, key=ranges.get)

    def split(self) -> tuple["ColorBucket", "ColorBucket"]:
        """
        делит сегмент пополам по медиане самого широкого канала
        сортировка идёт по значению канала, после чего список
        делится на две равные (по количеству уникальных цветов) части
        """
        channel = self.widest_channel()
        sorted_colors = sorted(self.colors, key=lambda item: item[0][channel])

        mid = len(sorted_colors) // 2
        return (
            ColorBucket(sorted_colors[:mid]),
            ColorBucket(sorted_colors[mid:]),
        )

    def weighted_average_color(self) -> RGBColor:
        """
        каждый цвет учитывается пропорционально частоте его появления
        на изображении, поэтому доминирующие цвета сильнее влияют
        на итоговый цвет палитры, а редкие лишь немного его корректируют.
        """
        total_weight = self.total_weight()
        if total_weight == 0:
            return (0, 0, 0)

        sums = [0, 0, 0]
        for color, weight in self.colors:
            for channel in Channel:
                sums[channel] += color[channel] * weight

        return (
            round(sums[Channel.RED] / total_weight),
            round(sums[Channel.GREEN] / total_weight),
            round(sums[Channel.BLUE] / total_weight),
        )


def _count_unique_colors(pixels: list[RGBColor]) -> list[WeightedColor]:
    counter = Counter(pixels)
    return list(counter.items())


def build_palette(pixels: list[RGBColor], palette_size: int = 256) -> list[RGBColor]:
    if not pixels:
        raise ValueError("Список пикселей пуст - нечего квантизировать")

    if palette_size < 1:
        raise ValueError("Размер палитры должен быть положительным числом")

    weighted_colors = _count_unique_colors(pixels)
    initial_bucket = ColorBucket(weighted_colors)

    buckets = [initial_bucket]

    while len(buckets) < palette_size:
        splittable = [b for b in buckets if len(b) > 1]
        if not splittable:
            break

        bucket_to_split = max(splittable, key=ColorBucket.total_weight)
        buckets.remove(bucket_to_split)

        left, right = bucket_to_split.split()
        buckets.extend([left, right])

    return [bucket.weighted_average_color() for bucket in buckets]


def find_nearest_color_index(color: RGBColor, palette: list[RGBColor]) -> int:
    """
    находит индекс ближайшего цвета в палитре по евклидову расстоянию

    используется для индексирования пикселей после построения палитры,
    а также после рассеивания ошибки, когда цвет
    пикселя уже не обязательно совпадает ни с одним цветом палитры
    """
    best_index = 0
    best_distance = float("inf")

    for index, palette_color in enumerate(palette):
        distance = sum(
            (color[channel] - palette_color[channel]) ** 2
            for channel in Channel
        )
        if distance < best_distance:
            best_distance = distance
            best_index = index

    return best_index