from __future__ import annotations

import struct
from dataclasses import dataclass

from core.median_cut import RGBColor

GIF_HEADER = b"GIF89a"
TRAILER_BYTE = b"\x3B"

IMAGE_SEPARATOR = b"\x2C"
EXTENSION_INTRODUCER = b"\x21"
GRAPHIC_CONTROL_LABEL = b"\xF9"
APPLICATION_LABEL = b"\xFF"

MAX_SUB_BLOCK_SIZE = 255


@dataclass
class GifFrame:
    width: int
    height: int
    indexed_pixels: list[int]
    delay_centiseconds: int  #задержка кадра в сотых долях секунды


def _palette_size_to_table_size_field(palette_size: int) -> int:
    if not (1 <= palette_size <= 256):
        raise ValueError("Размер палитры должен быть в диапазоне от 1 до 256")

    padded_size = 2
    while padded_size < palette_size:
        padded_size *= 2

    return padded_size.bit_length() - 2  # N = log2(padded_size) - 1


def _pad_palette(palette: list[RGBColor]) -> list[RGBColor]:
    padded_size = 2
    while padded_size < len(palette):
        padded_size *= 2

    padded = list(palette)
    padded.extend([(0, 0, 0)] * (padded_size - len(palette)))
    return padded


def _build_header() -> bytes:
    return GIF_HEADER


def _build_logical_screen_descriptor(
    width: int, height: int, palette_size: int
) -> bytes:
    table_size_field = _palette_size_to_table_size_field(palette_size)

    packed_fields = (
        (1 << 7)            # Global Color Table Flag
        | (7 << 4)          # Color Resolution
        | (0 << 3)          # Sort Flag
        | table_size_field  # Size of Global Color Table
    )

    return struct.pack(
        "<HHBBB",
        width,
        height,
        packed_fields,
        0,
        0,
    )


def _build_global_color_table(palette: list[RGBColor]) -> bytes:
    padded_palette = _pad_palette(palette)
    table = bytearray()
    for red, green, blue in padded_palette:
        table.extend((red, green, blue))
    return bytes(table)


def _build_netscape_loop_extension(loop_count: int = 0) -> bytes:
    extension = bytearray()
    extension += EXTENSION_INTRODUCER
    extension += APPLICATION_LABEL
    extension.append(11)                       # длина блока идентификации
    extension += b"NETSCAPE2.0"
    extension.append(3)                        # длина данных подблока
    extension.append(1)                         # индекс подблока (всегда 1)
    extension += struct.pack("<H", loop_count)   # количество повторов
    extension.append(0)                         # терминатор блока

    return bytes(extension)


def _build_graphic_control_extension(delay_centiseconds: int) -> bytes:
    packed_fields = (1 << 2)

    block = bytearray()
    block += EXTENSION_INTRODUCER
    block += GRAPHIC_CONTROL_LABEL
    block.append(4)  # размер блока данных
    block.append(packed_fields)
    block += struct.pack("<H", delay_centiseconds)
    block.append(0)
    block.append(0)  # терминатор блока

    return bytes(block)


def _build_image_descriptor(width: int, height: int) -> bytes:
    return struct.pack(
        "<BHHHHB",
        ord(IMAGE_SEPARATOR),
        0, # left
        0, # top
        width,
        height,
        0,
    )


def _split_into_sub_blocks(data: bytes) -> bytes:
    result = bytearray()
    offset = 0

    while offset < len(data):
        chunk = data[offset : offset + MAX_SUB_BLOCK_SIZE]
        result.append(len(chunk))
        result.extend(chunk)
        offset += MAX_SUB_BLOCK_SIZE

    result.append(0)  # терминатор блока данных изображения
    return bytes(result)


def _build_image_data_block(lzw_compressed: bytes, min_code_size: int) -> bytes:
    block = bytearray()
    block.append(min_code_size)
    block += _split_into_sub_blocks(lzw_compressed)
    return bytes(block)


def encode_gif(
    frames: list[GifFrame],
    palette: list[RGBColor],
    lzw_compressed_frames: list[bytes],
    min_code_size: int,
    loop_forever: bool = True,
) -> bytes:
    if not frames:
        raise ValueError("Список кадров пуст — нечего кодировать")

    if len(frames) != len(lzw_compressed_frames):
        raise ValueError("Количество кадров и сжатых данных не совпадает")

    canvas_width = frames[0].width
    canvas_height = frames[0].height

    output = bytearray()
    output += _build_header()
    output += _build_logical_screen_descriptor(canvas_width, canvas_height, len(palette))
    output += _build_global_color_table(palette)

    if len(frames) > 1 and loop_forever:
        output += _build_netscape_loop_extension(loop_count=0)

    for frame, compressed_data in zip(frames, lzw_compressed_frames):
        output += _build_graphic_control_extension(frame.delay_centiseconds)
        output += _build_image_descriptor(frame.width, frame.height)
        output += _build_image_data_block(compressed_data, min_code_size)

    output += TRAILER_BYTE

    return bytes(output)