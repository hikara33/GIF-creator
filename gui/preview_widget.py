from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class FramePreviewWidget(QWidget):
    frame_removed = pyqtSignal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._image_paths: list[Path] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QLabel("+-- КАДРЫ --+")
        header.setProperty("class", "section-title")
        layout.addWidget(header)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        self._preview_container = QWidget()
        self._preview_layout = QHBoxLayout(self._preview_container)
        self._preview_layout.setContentsMargins(8, 8, 8, 8)
        self._preview_layout.setSpacing(10)
        self._preview_layout.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )

        self._scroll_area.setWidget(self._preview_container)
        layout.addWidget(self._scroll_area)

        self._empty_label = QLabel("[ нет кадров ]")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setProperty("class", "info-text")
        layout.addWidget(self._empty_label)

    def set_frames(self, image_paths: list[Path]) -> None:
        self._image_paths = image_paths
        self._update_previews()

    def add_frame(self, image_path: Path) -> None:
        self._image_paths.append(image_path)
        self._update_previews()

    def clear_frames(self) -> None:
        self._image_paths.clear()
        self._update_previews()

    def get_image_paths(self) -> list[Path]:
        return self._image_paths.copy()

    def _update_previews(self) -> None:
        while self._preview_layout.count():
            item = self._preview_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._image_paths:
            self._empty_label.show()
            return

        self._empty_label.hide()

        for idx, image_path in enumerate(self._image_paths):
            preview = self._create_thumbnail(image_path, idx)
            self._preview_layout.addWidget(preview)

    def _create_thumbnail(self, image_path: Path, index: int) -> QWidget:
        container = QWidget()
        container.setFixedSize(100, 120)

        container.setStyleSheet(
            """
            QWidget {
                background-color: #ffffff;
                border-top: 3px solid #9ad8b8;
                border-left: 3px solid #9ad8b8;
                border-right: 3px solid #5a9e7a;
                border-bottom: 3px solid #5a9e7a;
            }
            QWidget:hover {
                background-color: #f0f8f4;
            }
            """
        )

        layout = QVBoxLayout(container)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(4)

        pixmap = QPixmap(str(image_path))
        scaled = pixmap.scaled(
            86, 68,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation
        )

        image_label = QLabel()
        image_label.setPixmap(scaled)
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setFixedSize(86, 68)
        image_label.setStyleSheet(
            "border: 2px solid #d8d0c8;"
        )
        layout.addWidget(image_label)

        filename = image_path.name
        if len(filename) > 10:
            filename = filename[:8] + ".."
        name_label = QLabel(filename)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setProperty("class", "info-text")
        name_label.setWordWrap(True)
        layout.addWidget(name_label)

        remove_btn = QLabel("X")
        remove_btn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        remove_btn.setFixedSize(18, 18)
        remove_btn.setStyleSheet(
            """
            QLabel {
                background-color: #ff8888;
                color: white;
                border-top: 2px solid #ffaaaa;
                border-left: 2px solid #ffaaaa;
                border-right: 2px solid #cc4444;
                border-bottom: 2px solid #cc4444;
                font-size: 12px;
                font-weight: bold;
                font-family: monospace;
            }
            QLabel:hover {
                background-color: #ff6666;
            }
            """
        )
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.mousePressEvent = lambda event, idx=index: self._on_remove(idx)
        layout.addWidget(remove_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        return container

    def _on_remove(self, index: int) -> None:
        if 0 <= index < len(self._image_paths):
            self._image_paths.pop(index)
            self._update_previews()
            self.frame_removed.emit(index)
