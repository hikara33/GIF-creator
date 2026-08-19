import io

import cv2
import numpy as np
from PIL import Image

from gui.worker import image_sequence_task, video_task


def create_test_frame(path, color, size=(20, 20)):
    image = Image.new("RGB", size, color)
    image.save(path)


def create_test_video(path, total_frames=15, fps=10.0, size=(32, 24)):
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        size,
    )
    for i in range(total_frames):
        frame = np.full((size[1], size[0], 3), i * 12, dtype=np.uint8)
        writer.write(frame)
    writer.release()


class TestImageSequenceTask:

    def test_builds_gif_from_image_paths(self, tmp_path):
        frame_paths = []    
        for i, color in enumerate([(255, 0, 0), (0, 255, 0), (0, 0, 255)]):
            path = tmp_path / f"frame_{i}.png"
            create_test_frame(path, color)
            frame_paths.append(path)

        task = image_sequence_task(
            frame_paths,
            delay_ms=100,
            palette_size=64,
            loop=True,
        )
        data = task(lambda _step, _total, _msg: None)

        assert data[:6] == b"GIF89a"
        assert data[-1] == 0x3B

    def test_reports_progress(self, tmp_path):
        frame_paths = []
        for i, color in enumerate([(255, 0, 0), (0, 255, 0)]):
            path = tmp_path / f"frame_{i}.png"
            create_test_frame(path, color)
            frame_paths.append(path)

        task = image_sequence_task(
            frame_paths,
            delay_ms=100,
            palette_size=64,
            loop=True,
        )
        reported = []
        task(lambda step, total, msg: reported.append((step, total, msg)))

        assert reported
        assert all(total == 5 for _, total, _ in reported)


class TestVideoTask:

    def test_builds_gif_from_video_fragment(self, tmp_path):
        video_path = tmp_path / "clip.mp4"
        create_test_video(video_path)

        task = video_task(
            video_path,
            start_sec=0.2,
            end_sec=1.0,
            target_fps=10.0,
            scale=1.0,
            palette_size=64,
            loop=True,
        )
        data = task(lambda _step, _total, _msg: None)

        assert data[:6] == b"GIF89a"
        assert data[-1] == 0x3B

    def test_reports_extraction_and_build_progress(self, tmp_path):
        video_path = tmp_path / "clip.mp4"
        create_test_video(video_path, total_frames=15, fps=10.0)

        task = video_task(
            video_path,
            start_sec=0.0,
            end_sec=1.0,
            target_fps=10.0,
            scale=0.5,
            palette_size=64,
            loop=True,
            use_dithering=False,
        )
        reported = []
        task(lambda step, total, msg: reported.append((step, total, msg)))

        messages = [msg for _, _, msg in reported]
        assert "Извлечение кадров" in messages
        assert any("Квантизация кадра" in msg for msg in messages)

    def test_delay_derived_from_fps(self, tmp_path):
        video_path = tmp_path / "clip.mp4"
        create_test_video(video_path, total_frames=15, fps=10.0)

        task = video_task(
            video_path,
            start_sec=0.0,
            end_sec=1.0,
            target_fps=10.0,
            scale=1.0,
            palette_size=64,
            loop=True,
        )
        data = task(lambda _step, _total, _msg: None)

        with Image.open(io.BytesIO(data)) as image:
            assert image.n_frames > 1
            assert image.info["duration"] == 100

    def test_scale_resizes_frames(self, tmp_path):
        video_path = tmp_path / "clip.mp4"
        create_test_video(video_path, total_frames=15, fps=10.0, size=(32, 24))

        task = video_task(
            video_path,
            start_sec=0.0,
            end_sec=1.0,
            target_fps=10.0,
            scale=0.5,
            palette_size=64,
            loop=True,
        )
        data = task(lambda _step, _total, _msg: None)

        with Image.open(io.BytesIO(data)) as image:
            assert image.size == (16, 12)