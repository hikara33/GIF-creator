from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QPointF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QMovie, QPainter, QPaintEvent
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from gui.icons import icon
from gui.resources.palette import PRIMARY

_STRIPE_WIDTH = 16
_ANIM_INTERVAL_MS = 40

_THUMB_SIZE = 56


class AnimatedProgressBar(QFrame):
    """Полоса прогресса высотой 6 px с анимированным диагональным паттерном."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("progress")
        self.setFixedHeight(6)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumWidth(220)

        self._value = 0
        self._processing = False
        self._offset = 0

        self._timer = QTimer(self)
        self._timer.setInterval(_ANIM_INTERVAL_MS)
        self._timer.timeout.connect(self._on_tick)

    # --- API ----------------------------------------------------------
    def set_value(self, percent: int) -> None:
        self._value = max(0, min(100, int(percent)))
        if self._value >= 100:
            self.set_processing(False)
        self.update()

    def set_processing(self, active: bool) -> None:
        self._processing = active
        if active and self._value < 100:
            self._timer.start()
        else:
            self._timer.stop()
            self.update()

    # --- отрисовка -----------------------------------------------------
    def _on_tick(self) -> None:
        self._offset = (self._offset + 3) % (_STRIPE_WIDTH * 2)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#E5E9EC"))
        painter.drawRoundedRect(self.rect(), 3, 3)

        chunk_width = self.width() * self._value / 100.0
        if chunk_width <= 1:
            painter.end()
            return

        painter.save()
        painter.setClipRect(0, 0, int(chunk_width), self.height())
        painter.setBrush(QColor(PRIMARY))
        painter.drawRoundedRect(self.rect(), 3, 3)

        if self._processing:
            painter.setPen(QColor(255, 255, 255, 70))
            begin = -_STRIPE_WIDTH + self._offset
            x = begin
            while x < chunk_width + _STRIPE_WIDTH:
                start = QPointF(x, self.height())
                end = QPointF(x + _STRIPE_WIDTH, 0)
                painter.drawLine(start, end)
                x += _STRIPE_WIDTH

        painter.restore()
        painter.end()


class BottomBar(QFrame):
    """Строка состояния: статус/прогресс слева, миниатюра и загрузка справа."""

    download_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("bottomBar")
        self.setProperty("panel", True)
        self.setFixedHeight(72)
        self._gif_movie: QMovie | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(14)

        status = QVBoxLayout()
        status.setContentsMargins(0, 0, 0, 0)
        status.setSpacing(6)

        caption_row = QHBoxLayout()
        caption_row.setContentsMargins(0, 0, 0, 0)

        self._caption_label = QLabel("Готово к работе")
        self._caption_label.setProperty("role", "helper")
        caption_row.addWidget(self._caption_label, stretch=1)

        self._percent_label = QLabel("")
        self._percent_label.setProperty("role", "mono")
        self._percent_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        caption_row.addWidget(self._percent_label)

        status.addLayout(caption_row)

        self._progress = AnimatedProgressBar()
        status.addWidget(self._progress)

        layout.addLayout(status, stretch=1)

        self._thumbnail = QLabel()
        self._thumbnail.setObjectName("gifThumbnail")
        self._thumbnail.setFixedSize(_THUMB_SIZE, _THUMB_SIZE)
        self._thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumbnail.setCursor(Qt.CursorShape.PointingHandCursor)
        self._thumbnail.setToolTip("Готовый GIF")
        self._thumbnail.hide()
        layout.addWidget(self._thumbnail)

        self._download_button = QPushButton("Скачать")
        self._download_button.setObjectName("downloadBtn")
        self._download_button.setProperty("buttonStyle", "primary")
        self._download_button.setIcon(icon("download", "#FFFFFF", 16))
        self._download_button.setFixedSize(140, 40)
        self._download_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._download_button.setEnabled(False)
        self._download_button.clicked.connect(self.download_requested)
        layout.addWidget(self._download_button)

    # --- API -------------------------------------------------------------
    @property
    def download_button(self) -> QPushButton:
        return self._download_button

    @property
    def thumbnail(self) -> QLabel:
        return self._thumbnail

    def set_gif_thumbnail(self, gif_path: str | Path) -> None:
        """Показывает играющую миниатюру готового GIF рядом с кнопкой."""
        self.clear_gif()
        movie = QMovie(str(gif_path))
        target = QSize(_THUMB_SIZE - 8, _THUMB_SIZE - 8)
        natural = movie.frameRect().size()
        if not natural.isEmpty():
            movie.setScaledSize(natural.scaled(target, Qt.AspectRatioMode.KeepAspectRatio))
        else:
            movie.setScaledSize(target)
        self._thumbnail.setMovie(movie)
        self._thumbnail.show()
        self._gif_movie = movie
        movie.start()

    def clear_gif(self) -> None:
        if self._gif_movie is not None:
            self._gif_movie.stop()
            self._gif_movie = None
        self._thumbnail.setMovie(None)
        self._thumbnail.hide()

    def set_caption(self, text: str) -> None:
        self._caption_label.setText(text)

    def set_percent(self, percent: int) -> None:
        self._progress.set_value(percent)
        self._percent_label.setText(f"{percent}%" if percent > 0 else "")

    def set_processing(self, active: bool) -> None:
        self._progress.set_processing(active)

    def set_error_hint(self, message: str) -> None:
        self._caption_label.setText(message)
        self._caption_label.setProperty("role", "error")
        self._repolish_caption()

    def reset(self) -> None:
        self._caption_label.setProperty("role", "helper")
        self._repolish_caption()
        self.set_caption("Готово к работе")
        self.set_percent(0)
        self.set_processing(False)
        self.clear_gif()

    def _repolish_caption(self) -> None:
        self._caption_label.style().unpolish(self._caption_label)
        self._caption_label.style().polish(self._caption_label)