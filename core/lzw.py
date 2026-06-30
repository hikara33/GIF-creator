"""
Модуль сжатия данных алгоритмом LZW (Lempel-Ziv-Welch) в формате,
совместимом со спецификацией GIF89a.

LZW — алгоритм сжатия без потерь, строящий словарь повторяющихся
последовательностей "на лету" в процессе кодирования. Вместо
повторяющейся последовательности символов в выходной поток
записывается короткий числовой код, ссылающийся на запись в словаре.

Особенности реализации именно под GIF:
- Коды упаковываются побитово (LSB-first — младший бит первым).
- Размер кода в битах растёт динамически по мере роста словаря:
  начинается с (min_code_size + 1) бит и увеличивается до 12 бит.
- Зарезервированы два специальных кода: Clear Code (сброс словаря)
  и End of Information (конец потока данных).
- При достижении максимального размера словаря (4096 записей)
  происходит автоматический сброс через Clear Code.
"""

from __future__ import annotations

from dataclasses import dataclass, field

MAX_CODE_SIZE_BITS = 12
MAX_DICTIONARY_SIZE = 1 << MAX_CODE_SIZE_BITS  # 4096


@dataclass
class LzwCodeTable:
    clear_code: int
    end_of_information_code: int
    min_code_size: int

    table: dict[tuple[int, ...], int] = field(init=False)
    next_code: int = field(init=False)
    code_size_bits: int = field(init=False)

    def __post_init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        base_size = self.clear_code  # количество цветов палитры
        self.table = {(i,): i for i in range(base_size)}
        self.next_code = self.end_of_information_code + 1
        self.code_size_bits = self.min_code_size + 1

    def lookup(self, sequence: tuple[int, ...]) -> int | None:
        return self.table.get(sequence)

    def add(self, sequence: tuple[int, ...]) -> None:
        self.table[sequence] = self.next_code
        self.next_code += 1

        if self.next_code > (1 << self.code_size_bits) and self.code_size_bits < MAX_CODE_SIZE_BITS:
            self.code_size_bits += 1

    def is_full(self) -> bool:
        return self.next_code >= MAX_DICTIONARY_SIZE


class BitPacker:
    def __init__(self) -> None:
        self._bit_buffer = 0
        self._bits_in_buffer = 0
        self._output = bytearray()

    def push_code(self, code: int, code_size_bits: int) -> None:
        self._bit_buffer |= code << self._bits_in_buffer
        self._bits_in_buffer += code_size_bits

        while self._bits_in_buffer >= 8:
            self._output.append(self._bit_buffer & 0xFF)
            self._bit_buffer >>= 8
            self._bits_in_buffer -= 8

    def finish(self) -> bytes:
        if self._bits_in_buffer > 0:
            self._output.append(self._bit_buffer & 0xFF)
            self._bit_buffer = 0
            self._bits_in_buffer = 0

        return bytes(self._output)


def compress(indices: list[int], palette_size: int) -> bytes:
    if not indices:
        raise ValueError("Список индексов пуст — нечего сжимать")

    min_code_size = _calculate_min_code_size(palette_size)
    clear_code = 1 << min_code_size
    end_of_information_code = clear_code + 1

    code_table = LzwCodeTable(
        clear_code=clear_code,
        end_of_information_code=end_of_information_code,
        min_code_size=min_code_size,
    )

    packer = BitPacker()
    packer.push_code(clear_code, code_table.code_size_bits)

    sequence_buffer: tuple[int, ...] = (indices[0],)

    for index in indices[1:]:
        candidate = sequence_buffer + (index,)

        if code_table.lookup(candidate) is not None:
            sequence_buffer = candidate
            continue

        packer.push_code(code_table.lookup(sequence_buffer), code_table.code_size_bits)
        code_table.add(candidate)

        if code_table.is_full():
            packer.push_code(clear_code, code_table.code_size_bits)
            code_table.reset()

        sequence_buffer = (index,)

    packer.push_code(code_table.lookup(sequence_buffer), code_table.code_size_bits)
    packer.push_code(end_of_information_code, code_table.code_size_bits)

    return packer.finish()


def _calculate_min_code_size(palette_size: int) -> int:
    if palette_size <= 4:
        return 2

    bits = (palette_size - 1).bit_length()
    return bits