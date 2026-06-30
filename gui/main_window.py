import tempfile
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPixmap
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.preview_widget import FramePreviewWidget
from gui.resources.pixel_theme import PIXEL_THEME_STYLESHEET
from gui.settings_panel import SettingsPanel


class GifWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(
        self,
        image_paths: list[Path],
        delay_ms: int,
        quality: int,
        loop: bool,
    ) -> None:
        super().__init__()
        self._image_paths = image_paths
        self._delay_ms = delay_ms
        self._quality = quality
        self._loop = loop

    def run(self) -> None:
        try:
            from PIL import Image

            images = []
            for path in self._image_paths:
                img = Image.open(str(path))
                if img.mode != "RGB":
                    img = img.convert("RGB")
                images.append(img)

            if not images:
                self.error.emit("Нет изображений")
                return

            temp_file = tempfile.NamedTemporaryFile(
                suffix=".gif", delete=False, mode="wb"
            )
            temp_path = temp_file.name
            temp_file.close()

            images[0].save(
                temp_path,
                save_all=True,
                append_images=images[1:],
                duration=self._delay_ms,
                loop=0 if self._loop else 1,
                optimize=True,
            )

            self.finished.emit(temp_path)

        except Exception as e:
            self.error.emit(str(e))


class GifPreviewLabel(QLabel):
    clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setProperty("class", "gif-preview")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    LEFT_COLUMN_WIDTH = 700
    RIGHT_COLUMN_WIDTH = 420
    GAP_WIDTH = 16

    def __init__(self) -> None:
        super().__init__()
        self._gif_path: Optional[str] = None
        self._setup_ui()
        self._apply_pixel_theme()
        self.setWindowTitle("GIF Creator")

        total_width = self.LEFT_COLUMN_WIDTH + self.GAP_WIDTH + self.RIGHT_COLUMN_WIDTH + 40  # margins
        self.setFixedSize(total_width, 750)

    def _setup_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(12)

        # Заголовок
        header = self._create_header()
        main_layout.addWidget(header)

        columns_container = QWidget()
        columns_layout = QHBoxLayout(columns_container)
        columns_layout.setContentsMargins(0, 0, 0, 0)
        columns_layout.setSpacing(self.GAP_WIDTH)

        left_panel = self._create_left_panel()
        left_panel.setFixedWidth(self.LEFT_COLUMN_WIDTH)
        columns_layout.addWidget(left_panel)

        right_panel = self._create_right_panel()
        right_panel.setFixedWidth(self.RIGHT_COLUMN_WIDTH)
        columns_layout.addWidget(right_panel)

        columns_layout.addStretch()

        main_layout.addWidget(columns_container)
        main_layout.addStretch()

    def _create_header(self) -> QWidget:
        header = QLabel("+--+ GIF CREATOR +--+")
        header.setProperty("class", "header-title")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return header

    def _create_left_panel(self) -> QWidget:
        panel = QWidget()
        panel.setProperty("class", "pixel-box")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        drop_zone = self._create_drop_zone()
        layout.addWidget(drop_zone)

        self._frame_preview = FramePreviewWidget()
        layout.addWidget(self._frame_preview)

        return panel

    def _create_drop_zone(self) -> QWidget:
        zone = QLabel()
        zone.setText(
            "+--------------------------+\n"
            "|  ПЕРЕТАЩИ СЮДА ФОТО      |\n"
            "|  или кликни для выбора   |\n"
            "+--------------------------+"
        )
        zone.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zone.setAcceptDrops(True)
        zone.setMinimumHeight(120)
        zone.setProperty("class", "drop-zone")
        zone.setCursor(Qt.CursorShape.PointingHandCursor)
        zone.mousePressEvent = lambda event: self._on_drop_zone_clicked()
        zone.dragEnterEvent = lambda event: self._on_drag_enter(event)
        zone.dropEvent = lambda event: self._on_drop(event)
        return zone

    def _create_right_panel(self) -> QWidget:
        panel = QWidget()
        panel.setProperty("class", "pixel-box")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        settings_title = QLabel("[ НАСТРОЙКИ ]")
        settings_title.setProperty("class", "section-title")
        layout.addWidget(settings_title)

        self._settings_panel = SettingsPanel()
        layout.addWidget(self._settings_panel)

        self._create_btn = QPushButton("[ СОЗДАТЬ GIF ]")
        self._create_btn.setProperty("class", "primary-button")
        self._create_btn.setMinimumHeight(45)
        self._create_btn.clicked.connect(self._on_create_gif)
        layout.addWidget(self._create_btn)

        result_title = QLabel("[ РЕЗУЛЬТАТ ]")
        result_title.setProperty("class", "section-title")
        layout.addWidget(result_title)

        self._gif_preview = GifPreviewLabel()
        self._gif_preview.setText("[ пусто ]")
        self._gif_preview.setMinimumHeight(180)
        self._gif_preview.clicked.connect(self._on_gif_preview_clicked)
        layout.addWidget(self._gif_preview)

        self._download_btn = QPushButton("[ СКАЧАТЬ ]")
        self._download_btn.setEnabled(False)
        self._download_btn.clicked.connect(self._on_download_gif)
        layout.addWidget(self._download_btn)

        layout.addStretch()

        return panel

    def _apply_pixel_theme(self) -> None:
        self.setStyleSheet(PIXEL_THEME_STYLESHEET)

    def _on_drag_enter(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def _on_drop(self, event: QDropEvent) -> None:
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            image_paths = []
            for url in urls:
                file_path = Path(url.toLocalFile())
                if file_path.suffix.lower() in [
                    ".png", ".jpg", ".jpeg", ".gif",
                    ".bmp", ".webp", ".tiff", ".tif"
                ]:
                    image_paths.append(file_path)
            if image_paths:
                self._frame_preview.set_frames(image_paths)
                self._update_create_button_state()

    def _on_drop_zone_clicked(self) -> None:
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter(
            "Images (*.png *.jpg *.jpeg *.gif *.bmp *.webp *.tiff *.tif)"
        )
        if file_dialog.exec():
            file_paths = [Path(f) for f in file_dialog.selectedFiles()]
            if file_paths:
                current = self._frame_preview.get_image_paths()
                current.extend(file_paths)
                self._frame_preview.set_frames(current)
                self._update_create_button_state()

    def _update_create_button_state(self) -> None:
        has_frames = len(self._frame_preview.get_image_paths()) > 0
        self._create_btn.setEnabled(has_frames)

    def _on_create_gif(self) -> None:
        image_paths = self._frame_preview.get_image_paths()
        if not image_paths:
            QMessageBox.warning(self, "Ошибка", "Загрузи изображения!")
            return

        self._create_btn.setEnabled(False)
        self._create_btn.setText("[ ЖДИ... ]")

        delay_ms = self._settings_panel.get_delay_ms()
        quality = self._settings_panel.get_quality()
        loop = self._settings_panel.is_looping()

        self._worker = GifWorker(image_paths, delay_ms, quality, loop)
        self._worker.finished.connect(self._on_gif_created)
        self._worker.error.connect(self._on_gif_error)
        self._worker.start()

    def _on_gif_created(self, gif_path: str) -> None:
        self._gif_path = gif_path
        pixmap = QPixmap(gif_path)
        scaled = pixmap.scaled(
            self._gif_preview.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation
        )
        self._gif_preview.setPixmap(scaled)
        self._download_btn.setEnabled(True)
        self._create_btn.setEnabled(True)
        self._create_btn.setText("[ СОЗДАТЬ GIF ]")

    def _on_gif_error(self, error_message: str) -> None:
        QMessageBox.critical(self, "Ошибка", error_message)
        self._create_btn.setEnabled(True)
        self._create_btn.setText("[ СОЗДАТЬ GIF ]")

    def _on_gif_preview_clicked(self) -> None:
        if self._gif_path:
            import subprocess
            import sys
            if sys.platform == "darwin":
                subprocess.call(["open", self._gif_path])
            elif sys.platform == "win32":
                subprocess.call(["start", self._gif_path], shell=True)
            else:
                subprocess.call(["xdg-open", self._gif_path])

    def _on_download_gif(self) -> None:
        if not self._gif_path:
            return
        file_dialog = QFileDialog()
        file_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        file_dialog.setNameFilter("GIF Images (*.gif)")
        file_dialog.setDefaultSuffix("gif")
        if file_dialog.exec():
            save_path = file_dialog.selectedFiles()[0]
            if save_path:
                import shutil
                shutil.copy2(self._gif_path, save_path)
                QMessageBox.information(self, "Готово", f"Сохранено:\n{save_path}")
