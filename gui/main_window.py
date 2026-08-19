from __future__ import annotations

import shutil

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QCloseEvent, QResizeEvent
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from gui.icons import icon
from gui.resources.palette import (
    GLOBAL_PADDING,
    SIDEBAR_WIDTH,
    SPACING,
    TEXT_SECONDARY,
)
from gui.resources.theme import THEME_STYLESHEET
from gui.types import MediaKind, UploadedMedia
from gui.video_editor import VideoEditorDialog
from gui.widgets.bottom_bar import BottomBar
from gui.widgets.frame_strip import FrameStrip
from gui.widgets.parameter_panel import ParameterPanel
from gui.widgets.preview_view import PreviewView
from gui.widgets.title_bar import TitleBar
from gui.widgets.upload_zone import UploadZone
from gui.worker import GifBuildWorker, image_sequence_task, video_task

_GIF_FILTER = "GIF Images (*.gif)"
_DEFAULT_HINT = "Перетащите сюда фото или видео"

_RESIZE_BORDER = 6

_VIDEO_EDITOR_HINT = (
    "Подберите фрагмент видео в редакторе: потяните маркеры по краям "
    "шкалы и нажмите «Обрезать» — в GIF попадёт только этот кусок"
)

_HELP_HTML = """
<h2>Изображения</h2>
<ul>
  <li>Загрузите несколько фото <b>JPG</b> или <b>PNG</b> — из них будет собрана анимация.</li>
  <li>Порядок кадров — это порядок выбранных файлов.</li>
  <li>Фотографии лучше брать <b>одного размера</b>: тогда GIF получится ровным и без сжатия по краям.</li>
  <li>Лишний кадр можно удалить крестиком на его миниатюре.</li>
</ul>
<h2>Видео</h2>
<ul>
  <li>Поддерживаются форматы <b>MP4</b>, <b>MOV</b>, <b>AVI</b> — одно видео за раз.</li>
  <li>Нажмите «Открыть редактор»: потяните маркеры по краям шкалы, чтобы выбрать фрагмент, и нажмите «Обрезать».</li>
  <li>Точные границы можно ввести в поля «Старт» и «Конец».</li>
  <li>В предпросмотре видео играет только выбранный фрагмент — так видно, что попадёт в GIF.</li>
</ul>
<h2>Параметры</h2>
<ul>
  <li><b>Фото:</b> скорость (задержка кадра в мс) и качество (размер палитры).</li>
  <li><b>Видео:</b> количество кадров в секунду (FPS) и размер кадра в процентах.</li>
  <li>Общие: режим «Дитеринг» (лучше переходы цветов) или «Быстрая» (скорость), и зацикливание анимации.</li>
</ul>
<h2>Создание GIF</h2>
<ul>
  <li>Нажмите кнопку <b>«Создать GIF»</b> внизу — сборка займёт несколько секунд.</li>
  <li>Готовый результат появится в предпросмотре, кнопка превратится в «Скачать».</li>
</ul>
"""


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FrameForge")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)

        self._media: UploadedMedia | None = None
        self._gif_path: str | None = None
        self._worker: GifBuildWorker | None = None
        self._pending_save = False

        self._video_duration_ms = 0
        self._video_playhead_ms = 0
        self._video_trim_ms = (0, 0)  # start_ms, end_ms выделенного фрагмента
        self._video_dialog: VideoEditorDialog | None = None

        self._title_bar: TitleBar | None = None

        self._setup_ui()
        self.setStyleSheet(THEME_STYLESHEET)
        self.resize(1180, 800)
        self.setMinimumSize(1000, 720)

    # построение интерфейса
    def _setup_ui(self) -> None:
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

        central = QWidget()
        central.setObjectName("appRoot")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._title_bar = TitleBar("FrameForge")
        self._title_bar.minimize_requested.connect(self.showMinimized)
        self._title_bar.maximize_requested.connect(self._toggle_maximize)
        self._title_bar.close_requested.connect(self.close)
        root.addWidget(self._title_bar)

        content = QWidget()
        content.setObjectName("appContent")
        column = QVBoxLayout(content)
        column.setContentsMargins(GLOBAL_PADDING, 12, GLOBAL_PADDING, GLOBAL_PADDING)
        column.setSpacing(SPACING)

        column.addWidget(self._build_header())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(SPACING)

        sidebar = self._build_sidebar()
        sidebar.setFixedWidth(SIDEBAR_WIDTH)
        body.addWidget(sidebar)

        center = self._build_center()
        body.addWidget(center, stretch=1)

        column.addLayout(body, stretch=1)

        self._bottom_bar = BottomBar()
        self._bottom_bar.download_requested.connect(self._on_download_clicked)
        column.addWidget(self._bottom_bar)

        root.addWidget(content, stretch=1)

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("appHeader")
        row = QHBoxLayout(header)
        row.setContentsMargins(4, 0, 4, 0)
        row.setSpacing(12)

        subtitle = QLabel("создайте анимацию за минуту")
        subtitle.setProperty("role", "helper")
        row.addWidget(subtitle)

        row.addStretch()

        media_hint = QLabel("Фото · Видео")
        media_hint.setProperty("role", "helper")
        row.addWidget(media_hint)

        self._help_button = QPushButton()
        self._help_button.setProperty("buttonStyle", "icon")
        self._help_button.setIcon(icon("help", TEXT_SECONDARY, 20))
        self._help_button.setToolTip("Справка по работе с приложением")
        self._help_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._help_button.clicked.connect(self._show_help)
        row.addWidget(self._help_button)

        return header

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")

        column = QVBoxLayout(sidebar)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(SPACING)

        self._upload_zone = UploadZone()
        self._upload_zone.upload_selected.connect(self._on_media_selected)
        column.addWidget(self._upload_zone)

        self._parameters = ParameterPanel()
        self._parameters.any_changed.connect(self._on_settings_changed)
        column.addWidget(self._parameters, stretch=1)

        return sidebar

    def _build_center(self) -> QWidget:
        center = QWidget()

        column = QVBoxLayout(center)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(SPACING)

        self._preview = PreviewView()
        self._preview.duration_changed.connect(self._on_video_duration_changed)
        self._preview.playhead_changed.connect(self._on_video_playhead_changed)
        column.addWidget(self._preview, stretch=1)

        # Контекстная зона: миниатюры фото либо приглашение к редактору видео.
        self._context = QWidget()
        context_layout = QVBoxLayout(self._context)
        context_layout.setContentsMargins(0, 0, 0, 0)
        context_layout.setSpacing(SPACING)

        self._frame_strip = FrameStrip()
        self._frame_strip.frame_removed.connect(self._on_frame_removed)
        self._frame_strip.hide()
        context_layout.addWidget(self._frame_strip)

        self._video_editor_card = self._build_video_editor_card()
        context_layout.addWidget(self._video_editor_card)

        column.addWidget(self._context)

        return center

    def _build_video_editor_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("videoEditorCard")
        card.hide()

        row = QHBoxLayout(card)
        row.setContentsMargins(20, 16, 20, 16)
        row.setSpacing(16)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(4)

        title = QLabel("Работа с видео")
        title.setProperty("headerLevel", "2")
        text_col.addWidget(title)

        hint = QLabel(_VIDEO_EDITOR_HINT)
        hint.setProperty("role", "helper")
        hint.setWordWrap(True)
        text_col.addWidget(hint)

        row.addLayout(text_col, stretch=1)

        self._video_edit_button = QPushButton("Открыть редактор")
        self._video_edit_button.setProperty("buttonStyle", "primary")
        self._video_edit_button.setIcon(icon("scissors", "#FFFFFF", 16))
        self._video_edit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._video_edit_button.setFixedSize(190, 40)
        self._video_edit_button.clicked.connect(self._open_video_editor)
        row.addWidget(self._video_edit_button)

        return card

    # сигналы загрузки и настроек
    def _on_media_selected(self, media: UploadedMedia) -> None:
        self._cancel_build()
        self._close_video_editor()
        self._video_duration_ms = 0
        self._video_playhead_ms = 0
        self._video_trim_ms = (0, 0)

        # Добор кадров: фото добавляются к уже загруженной последовательности.
        if (
            self._media is not None
            and self._media.kind is MediaKind.IMAGES
            and media.kind is MediaKind.IMAGES
        ):
            merged = list(self._media.paths)
            for path in media.paths:
                if path not in merged:
                    merged.append(path)
            media = UploadedMedia(MediaKind.IMAGES, tuple(merged))

        self._media = media
        self._invalidate_gif()
        self._upload_zone.clear_error()
        self._bottom_bar.reset()
        self._parameters.set_media_kind(media.kind)

        if media.kind is MediaKind.VIDEO:
            self._show_video_context(media)
        else:
            self._show_images_context(media)

        self._update_download_button()

    def _show_images_context(self, media: UploadedMedia) -> None:
        self._preview.load_image(media.primary_path)
        self._video_editor_card.hide()
        self._frame_strip.set_frames(list(media.paths))
        self._frame_strip.show()

    def _show_video_context(self, media: UploadedMedia) -> None:
        self._preview.load_video(media.primary_path)
        self._frame_strip.clear()
        self._frame_strip.hide()
        self._video_editor_card.show()

    def _on_frame_removed(self, _index: int) -> None:
        if self._media is None or self._media.kind is not MediaKind.IMAGES:
            return

        remaining = self._frame_strip.get_frames()
        if not remaining:
            self._media = None
            self._preview.clear()
            self._frame_strip.hide()
            self._upload_zone.set_hint(_DEFAULT_HINT)
        else:
            self._media = UploadedMedia(MediaKind.IMAGES, tuple(remaining))
            self._preview.load_image(remaining[0])
        self._invalidate_gif()

    def _on_settings_changed(self, *_args) -> None:
        if self._media is not None:
            self._invalidate_gif()

    def _on_video_duration_changed(self, duration_ms: int) -> None:
        self._video_duration_ms = max(0, duration_ms)
        if self._video_dialog is not None:
            self._video_dialog.trim_panel.set_duration_ms(self._video_duration_ms)
            self._video_dialog.trim_panel.set_playhead(self._video_playhead_ms)

    def _on_video_trim_changed(self, start_ms: int, end_ms: int) -> None:
        self._video_trim_ms = (max(0, start_ms), max(0, end_ms))
        self._preview.set_trim_range(self._video_trim_ms[0], self._video_trim_ms[1])
        self._on_settings_changed()

    def _on_video_playhead_changed(self, position_ms: int) -> None:
        self._video_playhead_ms = max(0, position_ms)
        if self._video_dialog is not None:
            self._video_dialog.set_playhead(position_ms)

    def _open_video_editor(self) -> None:
        if self._media is None or self._media.kind is not MediaKind.VIDEO:
            return

        if self._video_dialog is not None:
            self._video_dialog.show()
            self._video_dialog.raise_()
            self._video_dialog.activateWindow()
            return

        dialog = VideoEditorDialog(self._media.primary_path, self)
        dialog.trim_changed.connect(self._on_video_trim_changed)
        self._video_dialog = dialog

        if self._video_duration_ms > 0:
            dialog.trim_panel.set_duration_ms(self._video_duration_ms)
        start_ms, end_ms = self._video_trim_ms
        if end_ms > start_ms:
            dialog.trim_panel.set_trim(start_ms, end_ms)
        dialog.trim_panel.set_playhead(self._video_playhead_ms)
        dialog.show()

    def _close_video_editor(self) -> None:
        if self._video_dialog is not None:
            self._video_dialog.close()
            self._video_dialog = None

    def _video_trim_seconds(self) -> tuple[float, float]:
        start_ms, end_ms = self._video_trim_ms
        if self._video_dialog is not None:
            start_ms, end_ms = self._video_dialog.trim_panel.get_trim()
        if end_ms <= start_ms:
            end_ms = max(self._video_duration_ms, start_ms + 1000)
        return start_ms / 1000.0, end_ms / 1000.0

    # инвалидация результата
    def _invalidate_gif(self) -> None:
        self._gif_path = None
        self._bottom_bar.clear_gif()
        self._update_download_button()

    # построение GIF 
    def _on_download_clicked(self) -> None:
        if self._media is None:
            return

        if self._gif_path is not None:
            self._save_gif()
            return

        self._pending_save = True
        self._download().setEnabled(False)
        self._start_build()

    def _start_build(self) -> None:
        if self._media is None:
            return

        if self._media.kind is MediaKind.VIDEO:
            start_sec, end_sec = self._video_trim_seconds()
            task = video_task(
                self._media.primary_path,
                start_sec=start_sec,
                end_sec=end_sec,
                target_fps=self._parameters.get_target_fps(),
                scale=self._parameters.get_scale(),
                palette_size=self._parameters.get_palette_size(),
                loop=self._parameters.is_loop(),
                use_dithering=self._parameters.get_use_dithering(),
            )
        else:
            task = image_sequence_task(
                list(self._media.paths),
                delay_ms=self._parameters.get_delay_ms(),
                palette_size=self._parameters.get_palette_size(),
                loop=self._parameters.is_loop(),
                use_dithering=self._parameters.get_use_dithering(),
            )

        self._worker = GifBuildWorker(task)
        self._worker.progress.connect(self._on_build_progress)
        self._worker.finished.connect(self._on_build_finished)
        self._worker.failed.connect(self._on_build_failed)
        self._worker.start()

        self._bottom_bar.set_processing(True)
        self._bottom_bar.set_caption("Начинаю сборку…")
        self._bottom_bar.set_percent(0)

    def _on_build_progress(self, step: int, total: int, message: str) -> None:
        percent = round(step / total * 100)
        self._bottom_bar.set_percent(percent)
        self._bottom_bar.set_caption(f"{message} ({step}/{total})")

    def _on_build_finished(self, gif_path: str) -> None:
        self._gif_path = gif_path
        self._preview.show_gif(gif_path)
        self._bottom_bar.set_gif_thumbnail(gif_path)
        self._bottom_bar.set_percent(100)
        self._bottom_bar.set_processing(False)
        self._bottom_bar.set_caption("Готово")

        if self._pending_save:
            self._pending_save = False
            self._save_gif()

        self._worker = None
        self._update_download_button()

    def _on_build_failed(self, message: str) -> None:
        self._bottom_bar.set_processing(False)
        self._bottom_bar.set_error_hint(f"Ошибка: {message}")
        self._bottom_bar.set_percent(0)
        QMessageBox.critical(self, "Ошибка сборки GIF", message)
        self._pending_save = False
        self._worker = None
        self._update_download_button()

    # сохранение
    def _save_gif(self) -> None:
        if not self._gif_path:
            return

        destination, _ = QFileDialog.getSaveFileName(
            self, "Сохранить GIF", "", _GIF_FILTER
        )
        if not destination:
            return
        if not destination.lower().endswith(".gif"):
            destination += ".gif"

        try:
            shutil.copy2(self._gif_path, destination)
            self._bottom_bar.set_caption("Сохранено")
            QMessageBox.information(self, "Готово", f"Файл сохранён:\n{destination}")
        except OSError as error:
            QMessageBox.critical(self, "Ошибка сохранения", str(error))

    # кастомная рамка окна
    def _toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        if self._title_bar is not None:
            self._title_bar.set_maximized(self.isMaximized())

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.WindowStateChange and self._title_bar is not None:
            self._title_bar.set_maximized(self.isMaximized())
        super().changeEvent(event)

    def resizeEvent(self, event: QResizeEvent) -> None:
        # Без системной рамки максимизированное окно перекрывает панель задач:
        # ограничиваем его рабочей областью монитора.
        if self.isMaximized():
            screen = self.screen()
            if screen is not None:
                available = screen.availableGeometry()
                if self.geometry() != available:
                    self.setGeometry(available)
        super().resizeEvent(event)

    def eventFilter(self, obj, event) -> bool:
        # Ресайз окна за края: ловим нажатия/движения мыши в тонкой
        # полосе по периметру и запускаем нативную операцию изменения размера.
        if not self.isMaximized():
            etype = event.type()
            if etype == QEvent.Type.MouseButtonPress:
                if (
                    event.button() == Qt.MouseButton.LeftButton
                    and isinstance(obj, QWidget)
                    and obj.window() is self
                ):
                    edges = self._resize_edges_at(
                        self.mapFromGlobal(event.globalPosition().toPoint())
                    )
                    if edges:
                        handle = self.windowHandle()
                        if handle is not None:
                            handle.startSystemResize(edges)
                            return True
            elif (
                etype == QEvent.Type.MouseMove
                and isinstance(obj, QWidget)
                and obj.window() is self
            ):
                edges = self._resize_edges_at(
                    self.mapFromGlobal(event.globalPosition().toPoint())
                )
                if edges:
                    self.setCursor(self._cursor_for_edges(edges))
                elif self.cursor().shape() != Qt.CursorShape.ArrowCursor:
                    self.unsetCursor()
        return super().eventFilter(obj, event)

    def _resize_edges_at(self, pos) -> Qt.Edge:
        edges = Qt.Edge(0)
        width = self.width()
        height = self.height()
        x, y = pos.x(), pos.y()
        border = _RESIZE_BORDER

        if x <= border:
            edges = edges | Qt.Edge.LeftEdge
        elif x >= width - border:
            edges = edges | Qt.Edge.RightEdge
        if y <= border:
            edges = edges | Qt.Edge.TopEdge
        elif y >= height - border:
            edges = edges | Qt.Edge.BottomEdge
        return edges

    @staticmethod
    def _cursor_for_edges(edges: Qt.Edge) -> Qt.CursorShape:
        horizontal = bool(edges & (Qt.Edge.LeftEdge | Qt.Edge.RightEdge))
        vertical = bool(edges & (Qt.Edge.TopEdge | Qt.Edge.BottomEdge))
        if horizontal and vertical:
            if edges & Qt.Edge.LeftEdge and edges & Qt.Edge.TopEdge:
                return Qt.CursorShape.SizeFDiagCursor
            if edges & Qt.Edge.RightEdge and edges & Qt.Edge.BottomEdge:
                return Qt.CursorShape.SizeFDiagCursor
            return Qt.CursorShape.SizeBDiagCursor
        if horizontal:
            return Qt.CursorShape.SizeHorCursor
        if vertical:
            return Qt.CursorShape.SizeVerCursor
        return Qt.CursorShape.ArrowCursor

    #жизненный цикл
    def _cancel_build(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._cancel_build()
        self._close_video_editor()
        super().closeEvent(event)

    # вспомогательные обращения к вложенным виджетам 
    def _download(self) -> object:
        return self._bottom_bar.download_button

    # справка
    def _show_help(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Справка")
        dialog.setMinimumSize(520, 460)
        dialog.resize(560, 520)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Как работает FrameForge")
        title.setProperty("headerLevel", "1")
        layout.addWidget(title)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)
        browser.setHtml(_HELP_HTML)
        layout.addWidget(browser, stretch=1)

        close_button = QPushButton("Закрыть")
        close_button.setProperty("buttonStyle", "primary")
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.clicked.connect(dialog.close)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)

        dialog.show()

    def _update_download_button(self) -> None:
        """Активность и подпись кнопки: «Создать GIF» или «Скачать»."""
        running = self._worker is not None and self._worker.isRunning()
        button = self._download()
        button.setEnabled(self._media is not None and not running)
        button.setText("Скачать" if self._gif_path is not None else "Создать GIF")