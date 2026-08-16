from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

import numpy as np


class Channel(IntEnum):
    RED = 0
    GREEN = 1
    BLUE = 2


RGBColor = tuple[int, int, int]
WeightedColor = tuple[RGBColor, int]  # (цвет, количество вхождений)


@dataclass
class ColorBucket:

    def __init__(self, colors: np.ndarray, weights: np.ndarray) -> None:
        self.colors = colors
        self.weights = weights

    def __len__(self) -> int:
        return len(self.colors)

    def total_weight(self) -> int:
        return int(self.weights.sum())

    #ищем канал с этим же разбросом
    def widest_channel(self) -> Channel:
        ranges = self.colors.max(axis=0) - self.colors.min(axis=0)
        return int(ranges.argmax())

        
    def split(self) -> tuple[ColorBucket, ColorBucket]:
        ch = self.widest_channel()
        idx = np.argsort(self.colors[:, ch], kind="stable")
        c = self.colors[idx]
        w = self.weights[idx]
        mid = len(c) // 2

        return (
            ColorBucket(c[:mid].copy(), w[:mid].copy()),
            ColorBucket(c[mid:].copy(), w[mid:].copy()),
        )

    def weighted_average_color(self) -> RGBColor:
        avg = np.average(self.colors, axis=0, weights=self.weights)
        return (int(round(avg[0])), int(round(avg[1])), int(round(avg[2])))


def _pixels_to_unique_numpy(pixels: list[RGBColor]) -> tuple[np.ndarray, np.ndarray]:
    arr    = np.array(pixels, dtype=np.uint32)                        
    packed = (arr[:, 0] << 16) | (arr[:, 1] << 8) | arr[:, 2]       
 
    unique_packed, counts = np.unique(packed, return_counts=True)
 
    colors = np.stack([
        (unique_packed >> 16).astype(np.float32),
        ((unique_packed >> 8) & 0xFF).astype(np.float32),
        (unique_packed & 0xFF).astype(np.float32),
    ], axis=1)
 
    return colors, counts.astype(np.float32)


def build_palette(pixels: list[RGBColor], palette_size: int = 256) -> list[RGBColor]:
    if not pixels:
        raise ValueError("Список пикселей пуст - нечего квантизировать")

    if palette_size < 1:
        raise ValueError("Размер палитры должен быть положительным числом")

    colors, weights = _pixels_to_unique_numpy(pixels)
    target_size = min(palette_size, len(colors))

    buckets = [ColorBucket(colors, weights)]

    while len(buckets) < target_size:
        splittable = [b for b in buckets if len(b) > 1]
        if not splittable:
            break

        bucket_to_split = max(splittable, key=ColorBucket.total_weight)
        buckets.remove(bucket_to_split)

        left, right = bucket_to_split.split()
        buckets.extend([left, right])

    return [b.weighted_average_color() for b in buckets]

def find_nearest_color_index(color: RGBColor, palette: list[RGBColor]) -> int:
    pixel      = np.array(color,   dtype=np.float32)
    palette_np = np.array(palette, dtype=np.float32)
    diff       = pixel - palette_np
    return int(np.argmin(np.einsum("ij,ij->i", diff, diff)))


def find_nearest_palette_indices(
    pixels_flat: list[RGBColor],
    palette: list[RGBColor],
    chunk_size: int = 8192,
) -> list[int]:
    if not pixels_flat:
        return []
 
    px  = np.array(pixels_flat, dtype=np.float32)
    pal = np.array(palette,     dtype=np.float32)   
 
    pal_norms = np.einsum("mi,mi->m", pal, pal)   
 
    result = np.empty(len(px), dtype=np.int32)
 
    for start in range(0, len(px), chunk_size):
        chunk = px[start : start + chunk_size]                     
        px_norms = np.einsum("ni,ni->n", chunk, chunk)[:, None]    
        dot      = chunk @ pal.T                                    
        distances = px_norms - 2.0 * dot + pal_norms             
        result[start : start + chunk_size] = np.argmin(distances, axis=1)
 
    return result.tolist()