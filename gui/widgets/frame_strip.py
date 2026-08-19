from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

_FRAME_WIDTH = 112
_FRAME_HEIGHT = 108


class FrameStrip(QFrame):
    """Отображает загруженные кадры как карточки с возможностью удаления."""

    frame_removed = pyqtSignal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("frameStrip")
        self.setProperty("panel", True)
        self.setFixedHeight(150)

        self._paths: list[Path] = []
        self._build_ui()

    # --- построение интерфейса -----------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Кадры")
        title.setProperty("headerLevel", "2")
        header.addWidget(title)

        self._count_label = QLabel("")
        self._count_label.setProperty("role", "helper")
        header.addStretch()
        header.addWidget(self._count_label)
        layout.addLayout(header)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._container = QWidget()
        self._row = QHBoxLayout(self._container)
        self._row.setContentsMargins(0, 0, 0, 0)
        self._row.setSpacing(10)
        self._row.addStretch()

        self._scroll.setWidget(self._container)
        layout.addWidget(self._scroll)

        self._empty_label = QLabel("Кадры не добавлены")
        self._empty_label.setProperty("role", "helper")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.hide()
        layout.addWidget(self._empty_label)

    # --- публичное API -------------------------------------------------
    def set_frames(self, paths: list[Path]) -> None:
        self._paths = list(paths)
        self._rebuild()

    def clear(self) -> None:
        self._paths.clear()
        self._rebuild()

    def get_frames(self) -> list[Path]:
        return list(self._paths)

    # --- внутренняя логика -----------------------------------------------
    def _rebuild(self) -> None:
        while self._row.count():
            item = self._row.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()

        if not self._paths:
            self._count_label.setText("")
            self._empty_label.show()
            self._scroll.hide()
            return

        self._empty_label.hide()
        self._scroll.show()
        self._count_label.setText(f"{len(self._paths)} шт.")

        for index, path in enumerate(self._paths):
            self._row.insertWidget(self._row.count() - 1, self._make_card(path, index))

        self._row.addStretch()

    def _make_card(self, path: Path, index: int) -> QWidget:
        card = QWidget()
        card.setFixedSize(_FRAME_WIDTH, _FRAME_HEIGHT)
        card.setStyleSheet(
            "QWidget { background-color: #F4F6F8; border: 1px solid #E5E9EC;"
            " border-radius: 10px; }"
            "QWidget:hover { border-color: #10B981; }"
            "QWidget QLabel { border: none; background: transparent; }"
        )

        column = QVBoxLayout(card)
        column.setContentsMargins(6, 6, 6, 4)
        column.setSpacing(4)

        image_label = QLabel()
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setMinimumSize(_FRAME_WIDTH - 12, 62)
        pixmap = QPixmap(str(path))
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                _FRAME_WIDTH - 12,
                62,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            image_label.setPixmap(scaled)
        column.addWidget(image_label)

        name = path.name
        if len(name) > 12:
            name = name[:10] + "…"
        name_label = QLabel(name)
        name_label.setProperty("role", "helper")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setToolTip(path.name)
        column.addWidget(name_label)

        remove = QLabel("✕")
        remove.setAlignment(Qt.AlignmentFlag.AlignCenter)
        remove.setFixedSize(16, 16)
        remove.setStyleSheet(
            "QLabel { color: #9AA8AF; font-size: 12px; }"
            "QLabel:hover { color: #D92D20; }"
        )
        remove.setCursor(Qt.CursorShape.PointingHandCursor)
        remove.mousePressEvent = lambda event, i=index: self._on_remove(i)
        column.addWidget(remove, alignment=Qt.AlignmentFlag.AlignCenter)

        return card

    def _on_remove(self, index: int) -> None:
        if 0 <= index < len(self._paths):
            self._paths.pop(index)
            self._rebuild()
            self.frame_removed.emit(index)