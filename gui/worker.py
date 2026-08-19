from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QWidget

from io_module.gif_writer import write_gif

if TYPE_CHECKING:
    from core.pipeline import GifBuildSettings

ProgressCallback = Callable[[int, int, str], None]

GifTask = Callable[[ProgressCallback], bytes]

_VIDEO_MAX_FRAMES = 200


class BuildCancelled(Exception):
    """Сигнализирует об отмене текущей сборки внутри задачи."""


def image_sequence_task(
    image_paths: list[Path],
    *,
    delay_ms: int,
    palette_size: int,
    loop: bool,
    use_dithering: bool = True,
) -> GifTask:
    def _task(callback: ProgressCallback) -> bytes:
        from core.pipeline import build_gif
        from io_module.image_reader import read_image_sequence

        frames = read_image_sequence(list(image_paths))
        return build_gif(
            _settings_from_frames(
                frames, delay_ms, palette_size, loop, use_dithering
            ),
            progress_callback=callback,
        )

    return _task


def video_task(
    video_path: str | Path,
    *,
    start_sec: float,
    end_sec: float,
    target_fps: float,
    scale: float,
    palette_size: int,
    loop: bool,
    use_dithering: bool = True,
    max_frames: int = _VIDEO_MAX_FRAMES,
) -> GifTask:
    def _task(callback: ProgressCallback) -> bytes:
        from core.pipeline import build_gif
        from io_module.video_reader import extract_frames

        frames = extract_frames(
            video_path,
            start_sec=start_sec,
            end_sec=end_sec,
            target_fps=target_fps,
            scale=scale,
            max_frames=max_frames,
            progress_callback=lambda done, total: callback(
                done, total, "Извлечение кадров"
            ),
        )
        # Задержка кадра выводится из fps, чтобы GIF играл в том же темпе.
        delay_ms = max(20, round(1000 / target_fps))
        return build_gif(
            _settings_from_frames(
                frames, delay_ms, palette_size, loop, use_dithering
            ),
            progress_callback=callback,
        )

    return _task


def _settings_from_frames(
    frames: list[object],
    delay_ms: int,
    palette_size: int,
    loop: bool,
    use_dithering: bool,
) -> GifBuildSettings:
    from core.pipeline import GifBuildSettings

    return GifBuildSettings(
        preloaded_frames=frames,
        palette_size=palette_size,
        frame_delay_centiseconds=max(1, delay_ms // 10),
        loop_forever=loop,
        use_dithering=use_dithering,
    )


class GifBuildWorker(QThread):
    progress = pyqtSignal(int, int, str)  # step, total, message
    finished = pyqtSignal(str)  # абсолютный путь к временному GIF
    failed = pyqtSignal(str)

    def __init__(
        self,
        task: GifTask,
        *,
        parent: QWidget | None = None,
        work_dir: Path | None = None,
    ) -> None:
        super().__init__(parent)
        self._task = task
        self._work_dir = work_dir or Path(tempfile.gettempdir())
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            data = self._task(self._progress)
            if self._cancelled:
                return

            file_descriptor, temp_path = tempfile.mkstemp(
                suffix=".gif", dir=str(self._work_dir)
            )
            os.close(file_descriptor)

            written_path = write_gif(data, temp_path)
            if not self._cancelled:
                self.finished.emit(str(written_path))

        except BuildCancelled:
            return
        except Exception as error:  # noqa: BLE001 — любая ошибка показывается в GUI
            if not self._cancelled:
                self.failed.emit(str(error))

    def _progress(self, step: int, total: int, message: str) -> None:
        if self._cancelled:
            raise BuildCancelled
        self.progress.emit(step, total, message)