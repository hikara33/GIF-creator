
from __future__ import annotations

from PyQt6.QtCore import QPointF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent
from PyQt6.QtWidgets import QWidget

from gui.resources.palette import ACCENT, PRIMARY, PRIMARY_HOVER

_HANDLE_RADIUS = 12
_HANDLE_HIT = 18  # радиус зоны захвата ручки
_MIN_GAP_MS = 100

_TRACK_COLOR = QColor("#E6E9EC")
_TRACK_DISABLED = QColor("#C9D4D9")
_HANDLE_FILL = QColor("#FFFFFF")
_HANDLE_BORDER = QColor(PRIMARY)
_HANDLE_BORDER_HOVER = QColor(PRIMARY_HOVER)
_HANDLE_SHADOW = QColor(0, 0, 0, 40)


class RangeSlider(QWidget):
    """Слайдер выбора диапазона на одномерной шкале времени.

    Левый маркер меняет начало, правый — конец выделенного отрезка.
    Интервал ограничен [0; duration_ms].
    """

    value_changed = pyqtSignal(int, int)  # start_ms, end_ms
    seek_requested = pyqtSignal(int)  # перемотка по клику на шкале, мс

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._duration_ms = 0
        self._start_ms = 0
        self._end_ms = 0
        self._playhead_ms: int | None = None
        self._drag_handle: str | None = None
        self._hovered: str | None = None
        self.setMinimumHeight(46)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

    # --- публичное API -------------------------------------------------
    def set_range_ms(self, duration_ms: int) -> None:
        self._duration_ms = max(0, duration_ms)
        self._start_ms = min(self._start_ms, self._duration_ms)
        self._end_ms = min(self._end_ms, self._duration_ms)
        self.update()

    def set_value(self, start_ms: int, end_ms: int) -> None:
        if self._duration_ms <= 0:
            return
        start_ms = max(0, min(int(start_ms), self._duration_ms))
        end_ms = max(0, min(int(end_ms), self._duration_ms))
        if end_ms - start_ms < _MIN_GAP_MS:
            end_ms = min(self._duration_ms, start_ms + _MIN_GAP_MS)
        end_ms = max(end_ms, start_ms)
        if start_ms != self._start_ms or end_ms != self._end_ms:
            self._start_ms = start_ms
            self._end_ms = end_ms
            self.value_changed.emit(start_ms, end_ms)
        self.update()

    def set_playhead(self, playhead_ms: int | None) -> None:
        self._playhead_ms = playhead_ms
        self.update()

    def values(self) -> tuple[int, int]:
        return self._start_ms, self._end_ms

    # --- геометрия -------------------------------------------------------
    def _margin(self) -> float:
        return _HANDLE_RADIUS + 4

    def _x_for_time(self, ms: int) -> float:
        width = max(1, self.width() - 2 * self._margin())
        if self._duration_ms <= 0:
            return self._margin()
        return self._margin() + ms / self._duration_ms * width

    def _time_for_x(self, x: float) -> int:
        width = max(1, self.width() - 2 * self._margin())
        fraction = (x - self._margin()) / width
        return round(max(0.0, min(1.0, fraction)) * self._duration_ms)

    # --- отрисовка ---------------------------------------------------------
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.width() <= 2 * self._margin() or self.height() <= 0:
            painter.end()
            return

        center_y = self.height() / 2.0
        x_start = self._x_for_time(self._start_ms)
        x_end = self._x_for_time(self._end_ms)

        self._draw_track(painter, center_y)
        self._draw_selection(painter, x_start, x_end, center_y)
        self._draw_playhead(painter, center_y)
        self._draw_handle(painter, x_start, center_y, hovered=self._hovered == "start")
        self._draw_handle(painter, x_end, center_y, hovered=self._hovered == "end")

        painter.end()

    def _track_top(self, center_y: float) -> int:
        return round(center_y - 3)

    def _draw_track(self, painter: QPainter, center_y: float) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_TRACK_DISABLED if not self.isEnabled() else _TRACK_COLOR)
        painter.drawRoundedRect(
            round(self._margin()),
            self._track_top(center_y),
            self.width() - 2 * round(self._margin()),
            6,
            3,
            3,
        )

    def _draw_selection(
        self, painter: QPainter, x_start: float, x_end: float, center_y: float
    ) -> None:
        width = x_end - x_start
        if width <= 0:
            return
        painter.setBrush(QColor(PRIMARY if self.isEnabled() else "#9AA8AF"))
        painter.drawRoundedRect(
            round(x_start),
            self._track_top(center_y),
            round(width),
            6,
            3,
            3,
        )

    def _draw_playhead(self, painter: QPainter, center_y: float) -> None:
        if self._playhead_ms is None:
            return
        x = self._x_for_time(self._playhead_ms)
        painter.setBrush(QColor(ACCENT))
        painter.drawRect(int(x) - 1, int(center_y) - 14, 2, 28)

    def _draw_handle(
        self, painter: QPainter, x: float, center_y: float, *, hovered: bool
    ) -> None:
        border = _HANDLE_BORDER_HOVER if hovered else _HANDLE_BORDER
        if not self.isEnabled():
            border = QColor("#9AA8AF")

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_HANDLE_SHADOW)
        painter.drawEllipse(QPointF(x, center_y + 1), _HANDLE_RADIUS + 1, _HANDLE_RADIUS + 1)

        painter.setPen(border)
        painter.setBrush(_HANDLE_FILL)
        painter.drawEllipse(QPointF(x, center_y), _HANDLE_RADIUS, _HANDLE_RADIUS)

        painter.setPen(QColor(border))
        grip_start = round(center_y - 3)
        painter.drawLine(int(x) - 3, grip_start, int(x) - 3, grip_start + 6)
        painter.drawLine(int(x) + 3, grip_start, int(x) + 3, grip_start + 6)

    # --- взаимодействие -------------------------------------------------------
    def _handle_at(self, pos: QPointF) -> str | None:
        center_y = self.height() / 2.0
        start_x = self._x_for_time(self._start_ms)
        end_x = self._x_for_time(self._end_ms)
        if (pos - QPointF(start_x, center_y)).manhattanLength() <= _HANDLE_HIT:
            return "start"
        if (pos - QPointF(end_x, center_y)).manhattanLength() <= _HANDLE_HIT:
            return "end"
        return None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if not self.isEnabled():
            return
        handle = self._handle_at(event.position())
        if handle is not None:
            self._drag_handle = handle
            self._hovered = handle
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.update()
        else:
            self.seek_requested.emit(self._time_for_x(event.position().x()))
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        pos = event.position()
        if self._drag_handle is not None:
            ms = self._time_for_x(pos.x())
            if self._drag_handle == "start":
                self.set_value(ms, self._end_ms)
            else:
                self.set_value(self._start_ms, ms)
        else:
            hovered = self._handle_at(pos)
            if hovered != self._hovered:
                self._hovered = hovered
                self.setCursor(
                    Qt.CursorShape.ClosedHandCursor
                    if hovered
                    else Qt.CursorShape.PointingHandCursor
                )
                self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_handle = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        super().mouseReleaseEvent(event)