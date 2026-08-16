from __future__ import annotations

import numpy as np

from core.median_cut import RGBColor

try:
    from numba import njit as _njit

    @_njit
    def _dither_numba(
        buffer: np.ndarray,
        palette_np: np.ndarray,
        result: np.ndarray,
        height: int,
        width: int,
    ) -> None:
        for y in range(height):
            for x in range(width):
                r = max(0.0, min(255.0, buffer[y, x, 0]))
                g = max(0.0, min(255.0, buffer[y, x, 1]))
                b = max(0.0, min(255.0, buffer[y, x, 2]))

                best_idx = 0
                best_dist = 1e18
                for i in range(len(palette_np)):
                    dr = r - palette_np[i, 0]
                    dg = g - palette_np[i, 1]
                    db = b - palette_np[i, 2]
                    d = dr * dr + dg * dg + db * db
                    if d < best_dist:
                        best_dist = d
                        best_idx = i
                result[y, x] = best_idx

                er = r - palette_np[best_idx, 0]
                eg = g - palette_np[best_idx, 1]
                eb = b - palette_np[best_idx, 2]

                if x + 1 < width:
                    buffer[y, x + 1, 0] += er * 0.4375   # 7/16
                    buffer[y, x + 1, 1] += eg * 0.4375
                    buffer[y, x + 1, 2] += eb * 0.4375
                if y + 1 < height:
                    if x > 0:
                        buffer[y + 1, x - 1, 0] += er * 0.1875  # 3/16
                        buffer[y + 1, x - 1, 1] += eg * 0.1875
                        buffer[y + 1, x - 1, 2] += eb * 0.1875
                    buffer[y + 1, x, 0] += er * 0.3125   # 5/16
                    buffer[y + 1, x, 1] += eg * 0.3125
                    buffer[y + 1, x, 2] += eb * 0.3125
                    if x + 1 < width:
                        buffer[y + 1, x + 1, 0] += er * 0.0625  # 1/16
                        buffer[y + 1, x + 1, 1] += eg * 0.0625
                        buffer[y + 1, x + 1, 2] += eb * 0.0625

    _warmup_buf = np.ones((4, 4, 3), dtype=np.float32) * 128
    _warmup_pal = np.zeros((4, 3), dtype=np.float32)
    _warmup_res = np.empty((4, 4), dtype=np.int32)
    _dither_numba(_warmup_buf, _warmup_pal, _warmup_res, 4, 4)
    del _warmup_buf, _warmup_pal, _warmup_res
 
    _HAS_NUMBA = True

except ImportError:
    _HAS_NUMBA = False


def _dither_numpy(
        buffer: np.ndarray,
        palette_np: np.ndarray,
        result: np.ndarray,
        height: int,
        width: int,
) -> None:
    for y in range(height):
        for x in range(width):
            pixel = np.clip(buffer[y, x], 0.0, 255.0)
 
            diff = pixel - palette_np                         
            nearest_idx = int(
                np.argmin(np.einsum("ij,ij->i", diff, diff))  
            )
            result[y, x] = nearest_idx
 
            error = pixel - palette_np[nearest_idx]          
 
            if x + 1 < width:
                buffer[y, x + 1] += error * 0.4375
            if y + 1 < height:
                if x > 0:
                    buffer[y + 1, x - 1] += error * 0.1875
                buffer[y + 1, x] += error * 0.3125
                if x + 1 < width:
                    buffer[y + 1, x + 1] += error * 0.0625


def apply_dithering(
    pixels_2d: list[list[RGBColor]],
    palette: list[RGBColor],
) -> list[list[int]]:
    if not pixels_2d or not pixels_2d[0]:
        raise ValueError("Передано пустое изображение")
 
    height = len(pixels_2d)
    width = len(pixels_2d[0])
 
    buffer = np.array(pixels_2d, dtype=np.float32)   # (H, W, 3)
    palette_np = np.array(palette, dtype=np.float32)  # (M, 3)
    result = np.empty((height, width), dtype=np.int32)
 
    if _HAS_NUMBA:
        _dither_numba(buffer, palette_np, result, height, width)
    else:
        _dither_numpy(buffer, palette_np, result, height, width)
 
    return result.tolist()
