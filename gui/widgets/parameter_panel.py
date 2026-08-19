from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from gui.resources.palette import (
    BASE_FRAME_DELAY_MS,
    BASE_SCALE_PERCENT,
    BASE_VIDEO_FPS,
    DELAY_STEP_MS,
    MAX_DELAY_MS,
    MAX_SCALE_PERCENT,
    MAX_VIDEO_FPS,
    MIN_DELAY_MS,
    MIN_SCALE_PERCENT,
    MIN_VIDEO_FPS,
    SCALE_STEP_PERCENT,
)
from gui.types import QUALITY_PRESETS, MediaKind, clamp_delay_ms
from gui.widgets.segmented_control import SegmentedControl

#: Режимы квантизации: соответствует ``use_dithering`` в core.pipeline.
DITHER_MODES = (("Дитеринг", True), ("Быстрая", False))


class ParameterPanel(QFrame):
    """Настройки создаваемого GIF.

    Для изображений — скорость (задержка кадра в мс) и качество;
    для видео — частота кадров (fps) и размер в процентах. Общие для
    обоих типов: режим квантизации и зацикливание. Любое изменение
    сопровождается сигналом :attr:`any_changed`.
    """

    delay_ms_changed = pyqtSignal(int)
    quality_changed = pyqtSignal(int)  # размер палитры
    loop_changed = pyqtSignal(bool)
    any_changed = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setProperty("panel", True)
        self.setObjectName("paramsPanel")

        self._setup_ui()

    # --- построение интерфейса ---------------------------------------
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("Параметры")
        title.setProperty("headerLevel", "2")
        layout.addWidget(title)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_images_page())
        self._stack.addWidget(self._build_video_page())
        layout.addWidget(self._stack)

        layout.addWidget(self._build_mode_row())

        self._loop_checkbox = QCheckBox("Зациклить анимацию")
        self._loop_checkbox.setChecked(True)
        self._loop_checkbox.toggled.connect(self._on_loop_toggled)
        layout.addWidget(self._loop_checkbox)

        layout.addStretch()

    def _build_images_page(self) -> QWidget:
        page = QWidget()
        column = QVBoxLayout(page)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(10)

        self._delay_value = QLabel(f"{BASE_FRAME_DELAY_MS} мс")
        self._delay_value.setProperty("role", "mono")
        self._delay_slider = QSlider(Qt.Orientation.Horizontal)
        self._delay_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self._delay_slider.setToolTip("Пауза между кадрами в миллисекундах")
        self._configure_delay_slider()
        column.addWidget(self._slider_block(
            "Скорость",
            self._delay_value,
            self._delay_slider,
            f"Быстро · {MIN_DELAY_MS} мс",
            f"Медленно · {MAX_DELAY_MS} мс",
        ))

        column.addWidget(self._build_quality_row())
        return page

    def _build_video_page(self) -> QWidget:
        page = QWidget()
        column = QVBoxLayout(page)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(10)

        self._fps_value = QLabel(f"{BASE_VIDEO_FPS} fps")
        self._fps_value.setProperty("role", "mono")
        self._fps_slider = QSlider(Qt.Orientation.Horizontal)
        self._fps_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self._fps_slider.setToolTip("Сколько кадров в секунду попадает в GIF")
        self._configure_fps_slider()
        column.addWidget(self._slider_block(
            "Кадров в секунду",
            self._fps_value,
            self._fps_slider,
            f"Медленно · {MIN_VIDEO_FPS} fps",
            f"Плавно · {MAX_VIDEO_FPS} fps",
        ))

        self._scale_value = QLabel(f"{BASE_SCALE_PERCENT} %")
        self._scale_value.setProperty("role", "mono")
        self._scale_slider = QSlider(Qt.Orientation.Horizontal)
        self._scale_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self._scale_slider.setToolTip("Размер кадра GIF относительно исходного видео")
        self._configure_scale_slider()
        column.addWidget(self._slider_block(
            "Размер",
            self._scale_value,
            self._scale_slider,
            f"Меньше · {MIN_SCALE_PERCENT} %",
            f"Оригинал · {MAX_SCALE_PERCENT} %",
        ))

        return page

    def _build_quality_row(self) -> QWidget:
        container = QWidget()
        column = QVBoxLayout(container)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(6)

        line = QHBoxLayout()
        line.addWidget(self._make_row_label("Качество"))
        info = QLabel("размер GIF")
        info.setProperty("role", "helper")
        line.addStretch()
        line.addWidget(info)
        column.addLayout(line)

        self._quality = SegmentedControl(
            [(preset.label, preset.palette_size) for preset in QUALITY_PRESETS]
        )
        self._quality.set_current_data(QUALITY_PRESETS[-1].palette_size)
        self._quality.value_changed.connect(self._on_quality_changed)
        column.addWidget(self._quality)

        return container

    def _build_mode_row(self) -> QWidget:
        container = QWidget()
        column = QVBoxLayout(container)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(6)

        line = QHBoxLayout()
        line.addWidget(self._make_row_label("Режим"))
        info = QLabel("качество картинки / скорость")
        info.setProperty("role", "helper")
        line.addStretch()
        line.addWidget(info)
        column.addLayout(line)

        self._mode = SegmentedControl(DITHER_MODES)
        self._mode.set_current_data(True)
        self._mode.value_changed.connect(self._on_mode_changed)
        column.addWidget(self._mode)

        return container

    def _slider_block(
        self,
        title: str,
        value_label: QLabel,
        slider: QSlider,
        left_hint: str,
        right_hint: str,
    ) -> QWidget:
        container = QWidget()
        column = QVBoxLayout(container)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(6)

        line = QHBoxLayout()
        line.addWidget(self._make_row_label(title))
        line.addStretch()
        line.addWidget(value_label)
        column.addLayout(line)

        column.addWidget(slider)

        hint_line = QHBoxLayout()
        hint_left = QLabel(left_hint)
        hint_left.setProperty("role", "helper")
        hint_right = QLabel(right_hint)
        hint_right.setProperty("role", "helper")
        hint_line.addWidget(hint_left)
        hint_line.addStretch()
        hint_line.addWidget(hint_right)
        column.addLayout(hint_line)

        return container

    @staticmethod
    def _make_row_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setProperty("role", "helper")
        return label

    # --- настройка слайдеров ------------------------------------------
    def _configure_delay_slider(self) -> None:
        self._delay_slider.setRange(MIN_DELAY_MS, MAX_DELAY_MS)
        self._delay_slider.setSingleStep(DELAY_STEP_MS)
        self._delay_slider.setPageStep(10 * DELAY_STEP_MS)
        self._delay_slider.setValue(BASE_FRAME_DELAY_MS)
        self._delay_slider.valueChanged.connect(self._on_delay_changed)

    def _configure_fps_slider(self) -> None:
        self._fps_slider.setRange(MIN_VIDEO_FPS, MAX_VIDEO_FPS)
        self._fps_slider.setSingleStep(1)
        self._fps_slider.setPageStep(5)
        self._fps_slider.setValue(BASE_VIDEO_FPS)
        self._fps_slider.valueChanged.connect(self._on_fps_changed)

    def _configure_scale_slider(self) -> None:
        self._scale_slider.setRange(MIN_SCALE_PERCENT, MAX_SCALE_PERCENT)
        self._scale_slider.setSingleStep(SCALE_STEP_PERCENT)
        self._scale_slider.setPageStep(10)
        self._scale_slider.setValue(BASE_SCALE_PERCENT)
        self._scale_slider.valueChanged.connect(self._on_scale_changed)

    # --- сигналы --------------------------------------------------------
    def _on_delay_changed(self, value: int) -> None:
        value = clamp_delay_ms(value)
        self._delay_value.setText(f"{value} мс")
        self.delay_ms_changed.emit(value)
        self.any_changed.emit()

    def _on_fps_changed(self, value: int) -> None:
        self._fps_value.setText(f"{value} fps")
        self.any_changed.emit()

    def _on_scale_changed(self, value: int) -> None:
        self._scale_value.setText(f"{value} %")
        self.any_changed.emit()

    def _on_quality_changed(self, _index: int) -> None:
        self.quality_changed.emit(self.get_palette_size())
        self.any_changed.emit()

    def _on_mode_changed(self, _index: int) -> None:
        self.any_changed.emit()

    def _on_loop_toggled(self, checked: bool) -> None:
        self.loop_changed.emit(checked)
        self.any_changed.emit()

    # --- публичное API --------------------------------------------------
    def set_media_kind(self, kind: MediaKind) -> None:
        """Показывает страницу настроек под тип загруженного медиа."""
        index = 0 if kind is MediaKind.IMAGES else 1
        self._stack.setCurrentIndex(index)

    def get_delay_ms(self) -> int:
        return clamp_delay_ms(self._delay_slider.value())

    def get_palette_size(self) -> int:
        data = self._quality.current_data()
        return int(data) if data is not None else QUALITY_PRESETS[-1].palette_size

    def get_use_dithering(self) -> bool:
        data = self._mode.current_data()
        return bool(data) if data is not None else True

    def get_target_fps(self) -> int:
        return self._fps_slider.value()

    def get_scale(self) -> float:
        return self._scale_slider.value() / 100.0

    def is_loop(self) -> bool:
        return self._loop_checkbox.isChecked()

    def sync_labels(self) -> None:
        """Приводит текстовые лейблы к текущим значениям."""
        self._on_delay_changed(self._delay_slider.value())
        self._on_fps_changed(self._fps_slider.value())
        self._on_scale_changed(self._scale_slider.value())