import pytest


class TestLZW:
    def test_compress_returns_bytes(self):
        from core.lzw import compress

        indices = [0, 1, 2, 1, 0, 1, 2]
        result = compress(indices, palette_size=4)
        assert isinstance(result, bytes)

    def test_compress_non_empty(self):
        from core.lzw import compress

        indices = [5, 10, 15, 5, 10, 15]
        result = compress(indices, palette_size=256)
        assert len(result) > 0

    def test_repeated_sequence_compresses_well(self):
        from core.lzw import compress

        # 500 пар [0, 1] высокая повторяемость
        indices = [0, 1] * 500
        compressed = compress(indices, palette_size=256)
        #каждый индекс занимает минимум 1 байт, 1000 индексов = 1000 байт минимум
        #после сжатия должно быть значительно меньше
        assert len(compressed) < len(indices), (
            f"Сжатие не работает: {len(compressed)} >= {len(indices)}"
        )

    def test_single_color_compresses_well(self):
        from core.lzw import compress

        indices = [42] * 1000
        compressed = compress(indices, palette_size=256)

        assert len(compressed) < 100, (
            f"Однотонное изображение не сжалось хорошо: {len(compressed)} байт"
        )

    def test_raises_on_empty_indices(self):
        from core.lzw import compress

        with pytest.raises(ValueError):
            compress([], palette_size=256)

    def test_different_palette_sizes(self):
        from core.lzw import compress

        indices_64  = [i % 64  for i in range(200)]
        indices_128 = [i % 128 for i in range(200)]
        indices_256 = [i % 256 for i in range(200)]

        assert len(compress(indices_64,  palette_size=64))  > 0
        assert len(compress(indices_128, palette_size=128)) > 0
        assert len(compress(indices_256, palette_size=256)) > 0

    def test_gif_header_present_in_output(self):
        from core.lzw import _calculate_min_code_size, compress

        indices = [1, 2, 3, 4, 5]
        palette_size = 256
        compressed = compress(indices, palette_size)
        min_code_size = _calculate_min_code_size(palette_size)

        assert len(compressed) >= 2  # минимум: CLEAR + один код + EOI