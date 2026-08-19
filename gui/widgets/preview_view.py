from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QSize, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QMovie, QPixmap
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from gui.icons import icon
from gui.resources.palette import TEXT_DISABLED, TEXT_SECONDARY


class PreviewView(QFrame):
    """Карточка с превью и транспортом (Play/Pause/Restart/ZoomFit)."""

    playhead_changed = pyqtSignal(int)  # позиция в мс (только видео)
    duration_changed = pyqtSignal(int)  # длительность в мс (только видео)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("previewView")
        self.setProperty("panel", True)
        self.setMinimumSize(640, 360)

        self._mode: str | None = None  # "video" | "gif" | "image" | None
        self._gif_movie: QMovie | None = None
        self._image_source: QPixmap | None = None
        self._autoplay_pending = False
        self._trim_start_ms = 0
        self._trim_end_ms = 0

        self._setup_ui()

    # --- построение интерфейса -----------------------------------------
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 10)
        layout.setSpacing(10)

        self._stack = QStackedWidget()
        layout.addWidget(self._stack, stretch=1)

        self._placeholder = self._build_placeholder()
        self._stack.addWidget(self._placeholder)

        self._video_widget = QVideoWidget()
        self._video_widget.setStyleSheet(
            "background-color: #F4F6F8; border: none; border-radius: 10px;"
        )
        self._video_widget.setAutoFillBackground(True)
        self._stack.addWidget(self._video_widget)

        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setStyleSheet("border: none; background: #F4F6F8;")
        self._stack.addWidget(self._image_label)

        self._gif_label = QLabel()
        self._gif_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._gif_label.setStyleSheet("border: none; background: #F4F6F8;")
        self._stack.addWidget(self._gif_label)

        self._media_player = QMediaPlayer()
        self._media_player.setVideoOutput(self._video_widget)
        self._media_player.positionChanged.connect(self._on_position_changed)
        self._media_player.durationChanged.connect(self._on_duration_changed)
        self._media_player.mediaStatusChanged.connect(self._on_media_status_changed)

        layout.addWidget(self._build_transport())

    def _build_placeholder(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet(
            "QWidget { background-color: #F4F6F8; border: none; }"
        )
        column = QVBoxLayout(page)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(8)

        icon_label = QLabel()
        icon_label.setPixmap(icon("upload", TEXT_DISABLED, 56).pixmap(56, 56))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        column.addWidget(icon_label)

        title = QLabel("Перетащите фото или видео в зону загрузки")
        title.setProperty("role", "helper")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        column.addWidget(title)

        return page

    def _build_transport(self) -> QWidget:
        transport = QWidget()
        row = QHBoxLayout(transport)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self._play_button = self._make_icon_button("play", "Воспроизвести")
        self._play_button.clicked.connect(self._play)

        self._pause_button = self._make_icon_button("pause", "Пауза")
        self._pause_button.clicked.connect(self._pause)

        self._restart_button = self._make_icon_button("restart", "Заново")
        self._restart_button.clicked.connect(self._restart)

        self._zoom_button = self._make_icon_button("zoom_fit", "Подогнать под окно")
        self._zoom_button.clicked.connect(self._fit)

        for button in (
            self._play_button,
            self._pause_button,
            self._restart_button,
            self._zoom_button,
        ):
            row.addWidget(button)

        self._state_label = QLabel("")
        self._state_label.setProperty("role", "helper")
        row.addStretch()
        row.addWidget(self._state_label)
        return transport

    def _make_icon_button(self, icon_name: str, tooltip: str) -> QPushButton:
        button = QPushButton()
        button.setProperty("buttonStyle", "icon")
        button.setIcon(icon(icon_name, TEXT_SECONDARY))
        button.setToolTip(tooltip)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setEnabled(False)
        return button

    # --- публичное API -------------------------------------------------
    def load_video(self, video_path: str | Path) -> None:
        self._stop_current_media()
        self._mode = "video"
        self._autoplay_pending = True
        self._trim_start_ms = 0
        self._trim_end_ms = 0
        self._media_player.setSource(QUrl.fromLocalFile(str(video_path)))
        self._stack.setCurrentWidget(self._video_widget)
        self._set_transport_enabled(True)
        self._state_label.setText("Видео загружено")

    def set_trim_range(self, start_ms: int, end_ms: int) -> None:
        """Ограничивает воспроизведение видео выделенным фрагментом."""
        self._trim_start_ms = max(0, start_ms)
        self._trim_end_ms = max(self._trim_start_ms, end_ms)
        if self._mode == "video" and self._trim_end_ms > self._trim_start_ms:
            self._media_player.setPosition(self._trim_start_ms)

    def load_image(self, image_path: str | Path) -> None:
        self._stop_current_media()
        self._mode = "image"
        self._image_source = QPixmap(str(image_path))
        self._refresh_image()
        self._stack.setCurrentWidget(self._image_label)
        self._set_transport_enabled(False)
        self._state_label.setText("Кадры загружены")

    def show_gif(self, gif_path: str | Path) -> None:
        self._stop_current_media()
        self._mode = "gif"
        self._gif_movie = QMovie(str(gif_path))
        self._gif_movie.setScaledSize(
            self._fit_size(self._gif_movie.frameRect().size())
        )
        self._gif_label.setMovie(self._gif_movie)
        self._stack.setCurrentWidget(self._gif_label)
        self._gif_movie.start()
        self._set_transport_enabled(True)
        self._state_label.setText("GIF готов")

    def clear(self) -> None:
        self._stop_current_media()
        self._mode = None
        self._image_source = None
        self._stack.setCurrentWidget(self._placeholder)
        self._set_transport_enabled(False)
        self._state_label.setText("")

    # --- транспортая логика ---------------------------------------------
    def _play(self) -> None:
        if self._mode == "video":
            self._media_player.play()
            self._state_label.setText("Воспроизведение")
        elif self._mode == "gif" and self._gif_movie:
            self._gif_movie.start()
            self._state_label.setText("Воспроизведение")

    def _pause(self) -> None:
        if self._mode == "video":
            self._media_player.pause()
            self._state_label.setText("Пауза")
        elif self._mode == "gif" and self._gif_movie:
            self._gif_movie.setPaused(True)
            self._state_label.setText("Пауза")

    def _restart(self) -> None:
        if self._mode == "video":
            self._media_player.setPosition(0)
            self._state_label.setText("Сначала")
        elif self._mode == "gif" and self._gif_movie:
            self._gif_movie.jumpToFrame(0)
            self._gif_movie.start()
            self._state_label.setText("Сначала")

    def _fit(self) -> None:
        if self._mode == "image":
            self._refresh_image()
        elif self._mode == "gif" and self._gif_movie:
            self._gif_movie.setScaledSize(
                self._fit_size(self._gif_movie.frameRect().size())
            )
        self._state_label.setText("Подогнано к окну")

    def _refresh_image(self) -> None:
        if self._image_source is None:
            return
        scaled = self._image_source.scaled(
            self._image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._image_label.setPixmap(scaled)

    def _fit_size(self, natural: QSize) -> QSize:
        target = self._gif_label.size() - QSize(8, 8)
        if natural.isEmpty():
            return target
        return natural.scaled(target, Qt.AspectRatioMode.KeepAspectRatio)

    def _set_transport_enabled(self, enabled: bool) -> None:
        for button in (
            self._play_button,
            self._pause_button,
            self._restart_button,
            self._zoom_button,
        ):
            button.setEnabled(enabled)

    def _stop_current_media(self) -> None:
        if self._media_player.playbackState() != QMediaPlayer.PlaybackState.StoppedState:
            self._media_player.stop()
        if self._gif_movie is not None:
            self._gif_movie.stop()
            self._gif_movie = None

    def _on_position_changed(self, position_ms: int) -> None:
        if self._mode == "video":
            if self._trim_end_ms > self._trim_start_ms and position_ms >= self._trim_end_ms:
                self._media_player.setPosition(self._trim_start_ms)
            self.playhead_changed.emit(int(position_ms))

    def _on_duration_changed(self, duration_ms: int) -> None:
        self.duration_changed.emit(int(duration_ms))

    def _on_media_status_changed(self, status) -> None:
        if (
            self._mode == "video"
            and self._autoplay_pending
            and status == QMediaPlayer.MediaStatus.LoadedMedia
        ):
            self._autoplay_pending = False
            self._media_player.play()
            self._state_label.setText("Воспроизведение")