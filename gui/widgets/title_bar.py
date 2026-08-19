from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton

from gui.icons import icon
from gui.resources.palette import PRIMARY, TEXT_SECONDARY

_TITLE_BAR_HEIGHT = 40


class TitleBar(QFrame):
    """Верхняя полоса окна с названием и системными кнопками."""

    minimize_requested = pyqtSignal()
    maximize_requested = pyqtSignal()
    close_requested = pyqtSignal()

    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("titleBar")
        self.setFixedHeight(_TITLE_BAR_HEIGHT)
        self._maximized = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 8, 0)
        layout.setSpacing(10)

        logo = QLabel()
        logo.setPixmap(icon("loop", PRIMARY, 22).pixmap(22, 22))
        layout.addWidget(logo)

        title_label = QLabel(title)
        title_label.setProperty("headerLevel", "2")
        layout.addWidget(title_label)

        layout.addStretch()

        self._min_button = self._window_button("minimize", "Свернуть")
        self._min_button.clicked.connect(self.minimize_requested)
        layout.addWidget(self._min_button)

        self._max_button = self._window_button("maximize", "Развернуть")
        self._max_button.clicked.connect(self.maximize_requested)
        layout.addWidget(self._max_button)

        self._close_button = self._window_button("close", "Закрыть", close=True)
        self._close_button.clicked.connect(self.close_requested)
        layout.addWidget(self._close_button)

    def _window_button(self, icon_name: str, tooltip: str, *, close: bool = False) -> QPushButton:
        button = QPushButton()
        button.setProperty("windowButton", True)
        if close:
            button.setObjectName("titleCloseButton")
        button.setIcon(icon(icon_name, TEXT_SECONDARY, 16))
        button.setToolTip(tooltip)
        button.setFixedSize(42, 30)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    def set_maximized(self, maximized: bool) -> None:
        self._maximized = maximized
        name = "restore" if maximized else "maximize"
        tip = "Восстановить" if maximized else "Развернуть"
        self._max_button.setIcon(icon(name, TEXT_SECONDARY, 16))
        self._max_button.setToolTip(tip)

    # --- перетаскивание окна --------------------------------------------
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.window().windowHandle()
            if handle is not None:
                handle.startSystemMove()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.maximize_requested.emit()
        super().mouseDoubleClickEvent(event)