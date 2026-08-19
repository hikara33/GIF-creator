from __future__ import annotations

from PyQt6.QtCore import Qt, QTime, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from gui.resources.palette import TRIM_PANEL_HEIGHT
from gui.types import format_timecode
from gui.widgets.range_slider import RangeSlider

_PENDING = "…"
_MIN_GAP_MS = 100

_HOUR_MS = 3600 * 1000


def _time_to_ms(time: QTime) -> int:
    return (
        time.hour() * 3600 + time.minute() * 60 + time.second()
    ) * 1000


def _ms_to_time(ms: int) -> QTime:
    total_seconds = max(0, ms // 1000)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return QTime(hours, minutes, seconds)


class TrimPanel(QFrame):
    """Управление отрезком видео, попадающим в GIF.

    Маркеры на таймлайне или точные поля времени меняют диапазон.
    Сигнал :attr:`trim_changed` сообщает новые границы (мс),
    :attr:`seek_requested` — перемотку, :attr:`apply_requested` — нажатие
    на кнопку «Обрезать».
    """

    trim_changed = pyqtSignal(int, int)  # start_ms, end_ms
    seek_requested = pyqtSignal(int)  # позиция перемотки, мс
    apply_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setProperty("panel", True)
        self.setObjectName("trimPanel")
        self.setFixedHeight(TRIM_PANEL_HEIGHT)

        self._duration_ms = 0
        self._playhead_ms: int | None = None
        self._syncing = False

        self._setup_ui()

    # --- построение интерфейса -----------------------------------------
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(8)

        layout.addWidget(self._build_header())

        self._range_slider = RangeSlider()
        self._range_slider.value_changed.connect(self._on_range_changed)
        self._range_slider.seek_requested.connect(self.seek_requested)
        layout.addWidget(self._range_slider)

        layout.addWidget(self._build_time_row())

        layout.addWidget(self._build_controls())

    def _build_header(self) -> QWidget:
        header = QWidget()
        row = QHBoxLayout(header)
        row.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Обрезка видео")
        title.setProperty("headerLevel", "2")
        row.addWidget(title)

        hint = QLabel("тяните маркеры по краям — видео играет только внутри")
        hint.setProperty("role", "helper")
        row.addStretch()
        row.addWidget(hint)
        return header

    def _build_time_row(self) -> QWidget:
        row_widget = QWidget()
        row = QHBoxLayout(row_widget)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        start_caption = QLabel("Старт")
        start_caption.setProperty("role", "helper")
        row.addWidget(start_caption)

        self._start_edit = self._time_edit()
        self._start_edit.timeChanged.connect(self._on_start_time_changed)
        row.addWidget(self._start_edit)

        end_caption = QLabel("Конец")
        end_caption.setProperty("role", "helper")
        row.addWidget(end_caption)

        self._end_edit = self._time_edit()
        self._end_edit.timeChanged.connect(self._on_end_time_changed)
        row.addWidget(self._end_edit)

        self._duration_label = QLabel(f"Длительность  {_PENDING}")
        self._duration_label.setProperty("role", "mono")
        row.addStretch()
        row.addWidget(self._duration_label)
        return row_widget

    def _time_edit(self) -> QTimeEdit:
        edit = QTimeEdit()
        edit.setDisplayFormat("mm:ss")
        edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        edit.setButtonSymbols(QTimeEdit.ButtonSymbols.UpDownArrows)
        return edit

    def _build_controls(self) -> QWidget:
        controls = QWidget()
        row = QHBoxLayout(controls)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)

        self._reset_button = QPushButton("Сброс")
        self._reset_button.setProperty("buttonStyle", "outline")
        self._reset_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reset_button.clicked.connect(self._on_reset)
        row.addWidget(self._reset_button)

        row.addStretch()

        self._apply_button = QPushButton("Обрезать")
        self._apply_button.setProperty("buttonStyle", "primary")
        self._apply_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_button.clicked.connect(self.apply_requested)
        self._apply_button.setMinimumWidth(130)
        row.addWidget(self._apply_button)

        return controls

    # --- публичное API ---------------------------------------------------
    def set_duration_ms(self, duration_ms: int) -> None:
        self._duration_ms = max(0, duration_ms)
        if self._duration_ms > 0:
            self._range_slider.set_range_ms(self._duration_ms)
            self._apply_range(0, self._duration_ms)
            self.setEnabled(True)
        else:
            self.setEnabled(False)
        self._update_time_format()

    def set_playhead(self, playhead_ms: int | None) -> None:
        self._playhead_ms = playhead_ms
        self._range_slider.set_playhead(playhead_ms)

    def set_trim(self, start_ms: int, end_ms: int) -> None:
        """Восстанавливает ранее выбранный диапазон."""
        self._apply_range(start_ms, end_ms)

    def get_trim(self) -> tuple[int, int]:
        return self._range_slider.values()

    # --- внутренняя логика ---------------------------------------------
    def _update_time_format(self) -> None:
        display_format = "hh:mm:ss" if self._duration_ms >= _HOUR_MS else "mm:ss"
        for edit in (self._start_edit, self._end_edit):
            edit.setDisplayFormat(display_format)
            edit.setMaximumTime(_ms_to_time(self._duration_ms))

    def _on_range_changed(self, start_ms: int, end_ms: int) -> None:
        self._sync_editors()
        self._duration_label.setText(
            f"Длительность  {format_timecode(end_ms - start_ms)}"
        )
        self.trim_changed.emit(start_ms, end_ms)

    def _sync_editors(self) -> None:
        start_ms, end_ms = self.get_trim()
        self._syncing = True
        try:
            self._start_edit.setTime(_ms_to_time(start_ms))
            self._end_edit.setTime(_ms_to_time(end_ms))
        finally:
            self._syncing = False

    def _apply_range(self, start_ms: int, end_ms: int) -> None:
        """Применяет диапазон через слайдер (он сам клиппит и эмитит)."""
        self._range_slider.set_value(start_ms, end_ms)

    def _on_start_time_changed(self, time: QTime) -> None:
        if self._syncing or self._duration_ms <= 0:
            return
        start_ms, end_ms = self.get_trim()
        start_ms = max(0, min(_time_to_ms(time), end_ms - _MIN_GAP_MS))
        if start_ms != self.get_trim()[0]:
            self._apply_range(start_ms, end_ms)
        else:
            self._sync_editors()

    def _on_end_time_changed(self, time: QTime) -> None:
        if self._syncing or self._duration_ms <= 0:
            return
        start_ms, end_ms = self.get_trim()
        end_ms = min(self._duration_ms, max(_time_to_ms(time), start_ms + _MIN_GAP_MS))
        if end_ms != self.get_trim()[1]:
            self._apply_range(start_ms, end_ms)
        else:
            self._sync_editors()

    def _on_reset(self) -> None:
        self._apply_range(0, self._duration_ms)