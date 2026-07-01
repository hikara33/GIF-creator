from __future__ import annotations

from pathlib import Path


def write_gif(gif_bytes: bytes, output_path: str | Path) -> Path:
    path = Path(output_path)

    if path.suffix.lower() != ".gif":
        raise ValueError(
            f"Файл должен иметь расширение .gif, получено: '{path.suffix}'"
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gif_bytes)

    return path.resolve()
