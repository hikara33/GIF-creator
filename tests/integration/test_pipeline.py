from PIL import Image
from core.pipeline import GifBuildSettings, build_gif

def create_test_frame(path, color, size=(10, 10)):
    image = Image.new("RGB", size, color)
    image.save(path)


class TestPipeline:

    def test_full_pipeline_produces_valid_gif(self, tmp_path):
        colors = [
            (255, 0, 0),
            (0, 255, 0),
            (0, 0, 255),
        ]

        frame_paths = []

        for i, color in enumerate(colors):
            path = tmp_path / f"frame_{i}.png"
            create_test_frame(path, color, size=(30, 30))
            frame_paths.append(path)

        settings = GifBuildSettings(
            image_paths=frame_paths,
            palette_size=64,
            frame_delay_centiseconds=50,
            loop_forever=True,
        )

        gif_bytes = build_gif(settings)

        assert isinstance(gif_bytes, bytes)
        assert gif_bytes[:6] == b"GIF89a"
        assert gif_bytes[-1] == 0x3B

        output_path = tmp_path / "output.gif"
        output_path.write_bytes(gif_bytes)

        with Image.open(output_path) as image:
            assert image.format == "GIF"
            assert image.size == (30, 30)
            assert image.n_frames == 3


    def test_pipeline_respects_loop_setting(self, tmp_path):
        frame_paths = []

        for i, color in enumerate([
            (255, 0, 0),
            (0, 255, 0),
        ]):
            path = tmp_path / f"frame_{i}.png"
            create_test_frame(path, color)
            frame_paths.append(path)

        settings_loop = GifBuildSettings(
            image_paths=frame_paths,
            loop_forever=True,
        )

        settings_no_loop = GifBuildSettings(
            image_paths=frame_paths,
            loop_forever=False,
        )

        gif_loop = build_gif(settings_loop)
        gif_no_loop = build_gif(settings_no_loop)

        # NETSCAPE2.0 extension присутствует только
        # при loop_forever=True и количестве кадров > 1.
        assert b"NETSCAPE2.0" in gif_loop
        assert b"NETSCAPE2.0" not in gif_no_loop


    def test_progress_callback_called(self, tmp_path):
        path = tmp_path / "frame.png"
        create_test_frame(path, (100, 100, 100))

        steps_received = []

        def on_progress(step, total, message):
            steps_received.append((step, total, message))

        settings = GifBuildSettings(
            image_paths=[path],
        )

        build_gif(
            settings,
            progress_callback=on_progress,
        )

        assert len(steps_received) == 5

        steps = [step for step, _, _ in steps_received]

        assert steps == [1, 2, 3, 4, 5]

        assert all(
            total == 5
            for _, total, _ in steps_received
        )

        assert all(
            isinstance(message, str) and message
            for _, _, message in steps_received
        )