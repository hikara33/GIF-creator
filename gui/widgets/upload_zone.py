from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent, QMouseEvent
from PyQt6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout

from gui.icons import icon
from gui.resources.palette import PRIMARY, UPLOAD_ZONE_HEIGHT
from gui.types import ACCEPTED_EXTENSIONS, MediaKind, classify_files

_UPLOAD_HINT = "Перетащите сюда фото или видео"


class UploadZone(QFrame):
    """QFrame-зона с dashed-рамкой для перетаскивания файлов.

    Принимает изображения (jpg/jpeg/png) или одно видео (mp4/mov/avi).
    Результат отдаётся через сигнал :attr:`media_selected`.
    """

    upload_selected = pyqtSignal(object)  # UploadedMedia

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("uploadZone")
        self.setFixedHeight(UPLOAD_ZONE_HEIGHT)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._build_ui()

    # --- построение интерфейса -------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        icon_label = QLabel()
        icon_label.setPixmap(icon("upload", PRIMARY, 64).pixmap(64, 64))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self._title = QLabel(_UPLOAD_HINT)
        self._title.setProperty("role", "upload-title")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._title)

        hint = QLabel("Формат: JPG, PNG, MP4, MOV, AVI")
        hint.setProperty("role", "upload-sub")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        self.browse_button = QPushButton("Выбрать файлы")
        self.browse_button.setProperty("buttonStyle", "outline")
        self.browse_button.setIcon(icon("browse", PRIMARY))
        self.browse_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_button.clicked.connect(self._on_browse_clicked)
        layout.addWidget(self.browse_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self._error_label = QLabel("")
        self._error_label.setProperty("role", "error")
        self._error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._error_label.setWordWrap(True)
        self._error_label.hide()
        layout.addWidget(self._error_label)

    # --- API -------------------------------------------------------
    def set_hint(self, text: str) -> None:
        """Внешнее сообщение (например, имя загруженного файла)."""
        self._title.setText(text)

    def show_error(self, message: str) -> None:
        self._error_label.setText(message)
        self._error_label.show()

    def clear_error(self) -> None:
        self._error_label.clear()
        self._error_label.hide()

    # --- drag & drop ------------------------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            self._set_drag_state(True)
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragEnterEvent) -> None:
        event.acceptProposedAction()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        self._set_drag_state(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        self._set_drag_state(False)
        paths = [
            Path(url.toLocalFile())
            for url in event.mimeData().urls()
            if url.isLocalFile()
        ]
        if paths:
            self._submit([path for path in paths if path.exists()])
            event.acceptProposedAction()
        else:
            event.ignore()

    # --- события -----------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._open_file_dialog()
        super().mousePressEvent(event)

    def _on_browse_clicked(self) -> None:
        self._open_file_dialog()

    def _open_file_dialog(self) -> None:
        from PyQt6.QtWidgets import QFileDialog

        file_filter = (
            "Фото и видео (*.jpg *.jpeg *.png *.mp4 *.mov *.avi);;"
            "Изображения (*.jpg *.jpeg *.png);;"
            "Видео (*.mp4 *.mov *.avi)"
        )
        dialog = QFileDialog(self, "Выберите файлы")
        dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        dialog.setNameFilter(file_filter)
        if not dialog.exec():
            return

        selected = [Path(path) for path in dialog.selectedFiles()]
        self._submit(self._accepted_files(selected))

    # ---- внутренняя логика -------------------------------------------
    def _accepted_files(self, paths: list[Path]) -> list[Path]:
        accepted = [
            path for path in paths if path.suffix.lower() in ACCEPTED_EXTENSIONS
        ]
        unsupported = [path for path in paths if path not in accepted]
        if unsupported and not accepted:
            names = ", ".join(p.name for p in unsupported[:3])
            self.show_error(f"Формат не поддерживается: {names}")
        return accepted

    def _submit(self, paths: list[Path]) -> None:
        self.clear_error()
        if not paths:
            return

        media = classify_files(tuple(paths))
        if media is None:
            self.show_error("Нельзя смешивать фото и видео (или выбрать сразу 2 видео)")
            return

        if media.kind is MediaKind.VIDEO:
            self.set_hint(str(media.primary_path.name))
        else:
            self.set_hint(f"Кадры: {len(media.paths)}")
        self.upload_selected.emit(media)

    def _set_drag_state(self, active: bool) -> None:
        if self.property("dragActive") == active:
            return
        self.setProperty("dragActive", active)
        self.style().unpolish(self)
        self.style().polish(self)