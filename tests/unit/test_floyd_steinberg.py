import pytest

from core.floyd_steinberg import apply_dithering
from core.floyd_steinberg import _HAS_NUMBA

from core.median_cut import build_palette

class TestFloydSteinberg:
    def test_output_dimensions_match_input(self, random_image):
        W, H = 30, 20

        pixels_2d, palette = random_image
        result = apply_dithering(pixels_2d, palette)

        assert len(result) == H, f"Высота {len(result)} != {H}"
        assert all(len(row) == W for row in result), "Ширина строк не совпадает"

    def test_all_indices_in_palette_range(self, random_image):
        pixels_2d, palette = random_image
        result = apply_dithering(pixels_2d, palette)

        flat = [idx for row in result for idx in row]
        invalid = [i for i in flat if not (0 <= i < len(palette))]
        assert not invalid, f"Найдены индексы вне диапазона: {invalid[:5]}"

    def test_single_pixel_image(self):
        pixels_2d = [[(128, 128, 128)]]
        palette = [(0, 0, 0), (255, 255, 255), (128, 128, 128)]
        result = apply_dithering(pixels_2d, palette)

        assert len(result) == 1
        assert len(result[0]) == 1
        assert 0 <= result[0][0] < len(palette)

    def test_solid_color_image(self):
        color = (255, 0, 0)
        pixels_2d = [[color] * 10 for _ in range(10)]
        palette = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
        result = apply_dithering(pixels_2d, palette)

        flat = [idx for row in result for idx in row]
        #если красный точно в палитре, все пиксели должны ссылаться на индекс 0
        assert all(i == 0 for i in flat), (
            f"Ожидался индекс 0 для всех пикселей, получили: {set(flat)}"
        )

    def test_raises_on_empty_image(self):
        with pytest.raises(ValueError):
            apply_dithering([], [(255, 0, 0)])

    def test_numba_and_numpy_give_same_result(self):
        #тесты на намба. до оптимизации работать не будут
        if not _HAS_NUMBA:
            pytest.skip("numba не установлена")

        import numpy as np
        from core.floyd_steinberg import _dither_numpy

        import random
        random.seed(7)
        W, H = 15, 15
        pixels_flat = [(random.randint(0,255), random.randint(0,255), random.randint(0,255))
                       for _ in range(W * H)]
        pixels_2d = [pixels_flat[y*W:(y+1)*W] for y in range(H)]
        palette = build_palette(pixels_flat, 16)

        result_numba = apply_dithering(pixels_2d, palette)

        pal_np = np.array(palette, dtype=np.float32)
        buf = np.array(pixels_2d, dtype=np.float32)
        res = np.empty((H, W), dtype=np.int32)
        _dither_numpy(buf, pal_np, res, H, W)
        result_numpy = res.tolist()

        assert result_numba == result_numpy, "Numba и numpy дали разные результаты"