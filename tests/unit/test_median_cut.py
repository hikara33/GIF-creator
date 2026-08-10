import pytest

from core.median_cut import build_palette, find_nearest_color_index

def make_gradient_pixels(width=50, height=50):
    pixels = []
    for y in range(height):
        for x in range(width):
            r = int(x / width * 255)
            g = int(y / height * 255)
            b = 128
            pixels.append((r, g, b))
    return pixels

def make_two_color_pixels():
    return [(255, 0, 0)] * 500 + [(0, 0, 255)] * 500

def make_single_color_pixels():
    return [(100, 150, 200)] * 100


class TestBuildPalette:
    @pytest.mark.parametrize(
        "size",
        [8, 16, 64, 128, 256],
    )
    def test_returns_correct_number_of_colors(self, size):
        pixels = make_gradient_pixels()

        palette = build_palette(
            pixels,
            palette_size=size,
        )

        assert len(palette) <= size
        assert len(palette) > 0

    def test_all_colors_in_valid_range(self):
        pixels = make_gradient_pixels()

        palette = build_palette(
            pixels,
            palette_size=256,
        )

        for i, color in enumerate(palette):
            assert len(color) == 3, (
                f"Цвет {i} не RGB кортеж: {color}"
            )

            for channel_value in color:
                assert 0 <= channel_value <= 255, (
                    f"Значение канала {channel_value} "
                    f"вне [0, 255] в цвете {color}"
                )

    def test_two_color_image_gives_two_palette_entries(self):
        pixels = make_two_color_pixels()

        palette = build_palette(
            pixels,
            palette_size=256,
        )

        assert len(palette) == 2

    def test_single_color_image(self):
        pixels = make_single_color_pixels()

        palette = build_palette(
            pixels,
            palette_size=256,
        )

        assert len(palette) == 1
        assert palette[0] == (100, 150, 200)

    def test_weighted_average_dominant_color(self):
        pixels = [(255, 0, 0)] * 1000 + [(0, 0, 255)] * 10

        palette = build_palette(
            pixels,
            palette_size=1,
        )

        assert len(palette) == 1

        dominant = palette[0]

        assert dominant[0] > 200, (
            f"Доминирующий цвет не красный: {dominant}"
        )

    def test_raises_on_empty_pixels(self):
        with pytest.raises(ValueError):
            build_palette(
                [],
                palette_size=256,
            )

    def test_raises_on_invalid_palette_size(self):
        with pytest.raises(ValueError):
            build_palette(
                [(255, 0, 0)],
                palette_size=0,
            )

    def test_palette_cannot_have_more_colors_than_input(self):
        pixels = [(i * 25, i * 10, 0) for i in range(10)]

        palette = build_palette(
            pixels,
            palette_size=256,
        )

        assert len(palette) <= 10


class TestFindNearestColorIndex:

    def test_exact_match_returns_correct_index(self):
        palette = [
            (255, 0, 0),
            (0, 255, 0),
            (0, 0, 255),
        ]

        assert find_nearest_color_index(
            (255, 0, 0),
            palette,
        ) == 0

        assert find_nearest_color_index(
            (0, 255, 0),
            palette,
        ) == 1

        assert find_nearest_color_index(
            (0, 0, 255),
            palette,
        ) == 2

    def test_nearest_color_selection(self):
        palette = [
            (0, 0, 0),
            (255, 255, 255),
        ]

        assert find_nearest_color_index(
            (10, 10, 10),
            palette,
        ) == 0

        assert find_nearest_color_index(
            (240, 240, 240),
            palette,
        ) == 1

    def test_returns_correct_index_for_middle_color(self):
        palette = [
            (0, 0, 0),
            (255, 255, 255),
        ]

        index = find_nearest_color_index(
            (120, 120, 120),
            palette,
        )

        assert index == 0

    def test_returns_valid_index(self):
        palette = [
            (255, 0, 0),
            (0, 255, 0),
            (0, 0, 255),
        ]

        test_colors = [
            (10, 20, 30),
            (100, 100, 100),
            (200, 100, 50),
            (20, 200, 100),
        ]

        for color in test_colors:
            index = find_nearest_color_index(
                color,
                palette,
            )

            assert 0 <= index < len(palette)

    def test_single_color_palette_always_returns_zero(self):
        palette = [(100, 150, 200)]

        assert find_nearest_color_index(
            (0, 0, 0),
            palette,
        ) == 0

        assert find_nearest_color_index(
            (255, 255, 255),
            palette,
        ) == 0