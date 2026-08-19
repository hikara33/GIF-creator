import io
import struct

import pytest
from PIL import Image

from core.gif_encoder import (
    GifFrame,
    _split_into_sub_blocks,
    encode_gif,
)
from core.lzw import (
    _calculate_min_code_size,
    compress,
)


class TestGifEncoder:

    def _make_simple_gif(
        self,
        width=10,
        height=10,
        n_frames=1,
        delay=50,
        loop_forever=True,
    ):
        palette = [
            (255, 0, 0),
            (0, 255, 0),
            (0, 0, 255),
        ]

        frames = []
        compressed_frames = []

        for frame_number in range(n_frames):
            indexed_pixels = [
                (x + y + frame_number) % len(palette)
                for y in range(height)
                for x in range(width)
            ]

            frames.append(
                GifFrame(
                    width=width,
                    height=height,
                    indexed_pixels=indexed_pixels,
                    delay_centiseconds=delay,
                )
            )

            compressed_frames.append(
                compress(
                    indexed_pixels,
                    palette_size=len(palette),
                )
            )

        min_code_size = _calculate_min_code_size(len(palette))

        return encode_gif(
            frames=frames,
            palette=palette,
            lzw_compressed_frames=compressed_frames,
            min_code_size=min_code_size,
            loop_forever=loop_forever,
        )

    def test_starts_with_gif89a_header(self):
        gif_bytes = self._make_simple_gif()

        assert gif_bytes[:6] == b"GIF89a"

    def test_ends_with_trailer_byte(self):
        gif_bytes = self._make_simple_gif()

        assert gif_bytes[-1] == 0x3B

    def test_minimum_size(self):
        gif_bytes = self._make_simple_gif()

        assert len(gif_bytes) > 20

    def test_canvas_size_in_header(self):
        width = 15
        height = 25

        gif_bytes = self._make_simple_gif(
            width=width,
            height=height,
        )

        width_in_header = struct.unpack_from(
            "<H",
            gif_bytes,
            6,
        )[0]

        height_in_header = struct.unpack_from(
            "<H",
            gif_bytes,
            8,
        )[0]

        assert width_in_header == width
        assert height_in_header == height

    def test_multiframe_gif_larger_than_single_frame(self):
        single = self._make_simple_gif(n_frames=1)
        multi = self._make_simple_gif(n_frames=3)

        assert len(multi) > len(single)

    def test_valid_gif_readable_by_pillow(self):
        gif_bytes = self._make_simple_gif(
            width=20,
            height=20,
            n_frames=2,
            delay=100,
        )

        with Image.open(io.BytesIO(gif_bytes)) as img:
            assert img.format == "GIF"
            assert img.size == (20, 20)
            assert img.n_frames == 2

    def test_delay_stored_correctly(self):
        delay_cs = 75

        gif_bytes = self._make_simple_gif(
            delay=delay_cs,
        )

        with Image.open(io.BytesIO(gif_bytes)) as img:
            duration_ms = img.info["duration"]

        assert duration_ms == delay_cs * 10

    def test_loop_extension_present_when_enabled(self):
        gif_bytes = self._make_simple_gif(
            n_frames=2,
            loop_forever=True,
        )

        assert b"NETSCAPE2.0" in gif_bytes

    def test_loop_extension_absent_when_disabled(self):
        gif_bytes = self._make_simple_gif(
            n_frames=2,
            loop_forever=False,
        )

        assert b"NETSCAPE2.0" not in gif_bytes

    def test_loop_extension_only_added_for_multiple_frames(self):
        gif_bytes = self._make_simple_gif(
            n_frames=1,
            loop_forever=True,
        )

        assert b"NETSCAPE2.0" not in gif_bytes

    def test_raises_on_empty_frames(self):
        with pytest.raises(ValueError):
            encode_gif(
                frames=[],
                palette=[(255, 0, 0)],
                lzw_compressed_frames=[],
                min_code_size=2,
            )

    def test_raises_when_frame_count_does_not_match_compressed_data(self):
        frame = GifFrame(
            width=10,
            height=10,
            indexed_pixels=[0] * 100,
            delay_centiseconds=50,
        )

        with pytest.raises(ValueError):
            encode_gif(
                frames=[frame],
                palette=[(255, 0, 0)],
                lzw_compressed_frames=[],
                min_code_size=2,
            )


class TestSplitIntoSubBlocks:

    def test_empty_data_contains_only_terminator(self):
        result = _split_into_sub_blocks(b"")

        assert result == b"\x00"

    def test_small_data_has_one_sub_block(self):
        data = b"hello"

        result = _split_into_sub_blocks(data)

        assert result == b"\x05hello\x00"

    def test_data_is_split_into_255_byte_blocks(self):
        data = bytes(range(256)) * 2

        result = _split_into_sub_blocks(data)

        offset = 0
        blocks = []

        while True:
            block_size = result[offset]
            offset += 1

            if block_size == 0:
                break

            assert 1 <= block_size <= 255

            block = result[offset:offset + block_size]
            blocks.append(block)

            offset += block_size

        reconstructed = b"".join(blocks)

        assert reconstructed == data
        assert all(len(block) <= 255 for block in blocks)