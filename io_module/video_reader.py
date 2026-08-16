from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from io_module.image_reader import LoadedImage

SUPPORTED_VIDEO_EXTENSIONS = {
  ".mp4", ".mov", ".avi", ".webm",
  ".mkv", ".flv", ".wmv", ".m4v",
}

@dataclass
class VideoInfo:
  path: Path
  duration_sec: float
  fps: float #ориг фпс
  width: int
  height: int
  total_frames: int


def get_video_info(path: str | Path) -> VideoInfo:
  path = Path(path)

  if not path.exists():
    raise FileNotFoundError(f"Видеофайл не найден: {path}")

  if path.suffix.lower() not in SUPPORTED_VIDEO_EXTENSIONS:
    supported = ", ".join(sorted(SUPPORTED_VIDEO_EXTENSIONS))
    raise ValueError(
      f"Неподдерживаемый формат: {path.suffix}"
      f"Поддерживается: {supported}"
    )

  cap = cv2.VideoCapture(str(path))
  if not cap.isOpened():
    raise ValueError(
      f"Не удалось открыть файл {path.name}"
      f"Возможно, отсутствует кодек для этого формата"
    )

  try:
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration_sec = total_frames / fps if fps > 0 else 0.0
  finally:
    cap.release()

  return VideoInfo(
    path=path,
    duration_sec=round(duration_sec, 3),
    fps=fps,
    width=width,
    height=height,
    total_frames=total_frames,
  )


def extract_frames(
    path: str | Path,
    start_sec: float = 0.0,
    end_sec: float | None = None,
    target_fps: float = 10.0,
    scale: float = 1.0,
    max_frames: int = 200,
    progress_callback: Callable[[int, int], None] | None = None,
) -> list[LoadedImage]:
  path = Path(path)
 
  if not path.exists():
    raise FileNotFoundError(f"Видеофайл не найден: {path}")
 
  if target_fps <= 0:
    raise ValueError(f"target_fps должен быть > 0, получено: {target_fps}")
 
  if scale <= 0 or scale > 4:
    raise ValueError(f"scale должен быть в (0, 4], получено: {scale}")
 
  cap = cv2.VideoCapture(str(path))
  if not cap.isOpened():
    raise ValueError(f"Не удалось открыть '{path.name}'")

  try:
    video_fps    = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    orig_width   = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_height  = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    video_duration = total_frames / video_fps
    start_sec = max(0.0, min(start_sec, video_duration))
    end_sec = min(end_sec if end_sec is not None else video_duration, video_duration)

    if start_sec > end_sec:
      raise ValueError(
        f"Неверный диапазон: start={start_sec} >= end={end_sec}"
      )

    new_width = max(1, int(orig_width * scale))
    new_height = max(1, int(orig_height * scale))

    frame_interval_sec = 1.0 / target_fps

    #временные метки всех кадров которые нужно извлечь 
    timestamps = []
    t = start_sec
    while t < end_sec:
      timestamps.append(t)
      t+= frame_interval_sec

    timestamps = timestamps[:max_frames]
    total_to_extract = len(timestamps)

    if total_to_extract == 0:
      raise ValueError(
        f"В диапазоне [{start_sec:.1f}s, {end_sec:.1f}s]"
        f"нет кадров при FPS={target_fps}"
      )

    cap.set(cv2.CAP_PROP_POS_MSEC, start_sec * 1000)

    loaded_frames: list[LoadedImage] = []
    last_frame_pos_ms = -1.0

    for i, target_ms in enumerate(t * 1000 for t in timestamps):
      current_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
      if target_ms - current_ms > (1000.0 / video_fps) * 2:
        cap.set(cv2.CAP_PROP_POS_MSEC, target_ms)

      ret, bgr_frame = cap.read()
      if not ret:
        break

      rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)

      if scale != 1.0:
        rgb_frame = cv2.resize(
          rgb_frame,
          (new_width, new_height),
          interpolation=cv2.INTER_AREA,
        )

      pixels_2d = _numpy_frame_to_pixels_2d(rgb_frame)
 
      loaded_frames.append(LoadedImage(
        width=new_width,
        height=new_height,
        pixels_2d=pixels_2d,
        source_path=path,
      ))
 
      if progress_callback is not None:
        progress_callback(i + 1, total_to_extract)

  finally:
    cap.release()

  if not loaded_frames:
    raise ValueError(
      f"Не удалось извлечь ни одного кадра из {path.name}"
      f"в диапазоне [{start_sec:.1f}s, {end_sec:.1f}s]"
    )

  return loaded_frames


def _numpy_frame_to_pixels_2d(frame: np.ndarray) -> list[list[tuple[int, int, int]]]:
  raw = frame.tolist()
  return [
    [tuple(pixel) for pixel in row]
    for row in raw
  ]

def estimate_gif_frames(
    start_sec: float,
    end_sec: float,
    target_fps: float,
    max_frames: int = 200,
) -> int:
  if end_sec <= start_sec or target_fps <= 0:
    return 0
  duration = end_sec - start_sec
  return min(int(duration * target_fps), max_frames)

