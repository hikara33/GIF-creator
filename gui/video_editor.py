"""Отдельное окно для работы с видео: обрезка фрагмента и настройки."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.icons import icon
from gui.resources.palette import TEXT_SECONDARY
from gui.widgets.trim_panel import TrimPanel


class VideoEditorDialog(QDialog):
    """Немодальное окно редактирования видео.

    Собственный плеер для перемотки и панель обрезки ``TrimPanel``.
    Выбранный диапазон пробрасывается наружу сигналом :attr:`trim_changed`,
    чтобы главное окно не пересобирало GIF на устаревших границах.
    """

    trim_changed = pyqtSignal(int, int)  # start_ms, end_ms

    def __init__(self, video_path: str | Path, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("videoEditor")
        self.setWindowTitle("Редактор видео")
        self.setMinimumSize(760, 620)
        self.resize(880, 700)
        self.setWindowFlag(Qt.WindowType.Window)

        self._video_path = Path(video_path)
        self._video_player = QMediaPlayer(self)
        self._autoplay_pending = True

        self._setup_ui()
        self._wire_signals()
        self._video_player.setSource(
            QUrl.fromLocalFile(str(self._video_path))
        )

    # --- построение интерфейса -----------------------------------------
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        layout.addWidget(self._build_header())

        # Рабочий плеер для перемотки по кадрам будущего GIF.
        layout.addWidget(self._build_preview_editor(), stretch=1)

        self._trim_panel = TrimPanel()
        layout.addWidget(self._trim_panel)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.addStretch()

        close_button = QPushButton("Закрыть")
        close_button.setProperty("buttonStyle", "outline")
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.clicked.connect(self.close)
        controls.addWidget(close_button)
        layout.addLayout(controls)

    def _build_header(self) -> QWidget:
        header = QWidget()
        row = QHBoxLayout(header)
        row.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Редактор видео")
        title.setProperty("headerLevel", "1")
        row.addWidget(title)

        file_label = QLabel(self._video_path.name)
        file_label.setProperty("role", "helper")
        row.addStretch()
        row.addWidget(file_label)
        return header

    def _build_preview_editor(self) -> QWidget:
        frame = QFrame()
        frame.setProperty("panel", True)

        column = QVBoxLayout(frame)
        column.setContentsMargins(12, 12, 12, 12)
        column.setSpacing(10)

        self._video_widget = QVideoWidget()
        self._video_widget.setStyleSheet(
            "background-color: #F4F6F8; border-radius: 10px; border: none;"
        )
        self._video_widget.setAutoFillBackground(True)
        self._video_widget.setMinimumHeight(240)
        column.addWidget(self._video_widget, stretch=1)

        transport = QHBoxLayout()
        transport.setContentsMargins(0, 0, 0, 0)
        transport.setSpacing(8)

        self._play_button = self._transport_button("play", "Воспроизвести")
        self._play_button.clicked.connect(self._play)
        self._pause_button = self._transport_button("pause", "Пауза")
        self._pause_button.clicked.connect(self._pause)
        self._restart_button = self._transport_button("restart", "С начала")
        self._restart_button.clicked.connect(self._restart)

        for button in (
            self._play_button,
            self._pause_button,
            self._restart_button,
        ):
            transport.addWidget(button)

        self._state_label = QLabel("")
        self._state_label.setProperty("role", "helper")
        transport.addStretch()
        transport.addWidget(self._state_label)

        column.addLayout(transport)
        return frame

    def _transport_button(self, icon_name: str, tooltip: str) -> QPushButton:
        button = QPushButton()
        button.setProperty("buttonStyle", "icon")
        button.setIcon(icon(icon_name, TEXT_SECONDARY))
        button.setToolTip(tooltip)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    # --- сигналы ---------------------------------------------------------
    def _wire_signals(self) -> None:
        self._trim_panel.trim_changed.connect(self.trim_changed)
        self._trim_panel.trim_changed.connect(self._on_trim_changed)
        self._trim_panel.seek_requested.connect(self._seek)
        self._trim_panel.apply_requested.connect(self._on_apply)
        self._video_player.setVideoOutput(self._video_widget)
        self._video_player.positionChanged.connect(self._on_position_changed)
        self._video_player.durationChanged.connect(self._on_duration_changed)
        self._video_player.mediaStatusChanged.connect(self._on_media_status_changed)

    # --- публичное API ---------------------------------------------------
    @property
    def trim_panel(self) -> TrimPanel:
        return self._trim_panel

    def set_playhead(self, position_ms: int) -> None:
        self._trim_panel.set_playhead(position_ms)

    def _play(self) -> None:
        start_ms, end_ms = self._trim_panel.get_trim()
        position = self._video_player.position()
        if end_ms > start_ms and (position < start_ms or position >= end_ms):
            self._video_player.setPosition(start_ms)
        self._video_player.play()
        self._state_label.setText("Воспроизведение")

    def _pause(self) -> None:
        self._video_player.pause()
        self._state_label.setText("Пауза")

    def _restart(self) -> None:
        start_ms, _end_ms = self._trim_panel.get_trim()
        self._video_player.setPosition(start_ms)
        self._video_player.play()
        self._state_label.setText("С начала")

    def _seek(self, position_ms: int) -> None:
        self._video_player.setPosition(position_ms)

    def _on_position_changed(self, position_ms: int) -> None:
        self._trim_panel.set_playhead(int(position_ms))
        start_ms, end_ms = self._trim_panel.get_trim()
        if end_ms > start_ms and position_ms >= end_ms:
            self._video_player.setPosition(start_ms)

    def _on_duration_changed(self, duration_ms: int) -> None:
        self._trim_panel.set_duration_ms(int(duration_ms))
        self._trim_panel.set_playhead(0)

    def _on_media_status_changed(self, status) -> None:
        if status == QMediaPlayer.MediaStatus.LoadedMedia and self._autoplay_pending:
            self._autoplay_pending = False
            self._play()

    def _on_trim_changed(self, start_ms: int, end_ms: int) -> None:
        position = self._video_player.position()
        if end_ms > start_ms and (position < start_ms or position >= end_ms):
            self._video_player.setPosition(start_ms)

    def _on_apply(self) -> None:
        """Кнопка «Обрезать»: фиксирует диапазон и закрывает редактор."""
        start_ms, end_ms = self._trim_panel.get_trim()
        self.trim_changed.emit(start_ms, end_ms)
        self.close()