from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QSlider,
    QVBoxLayout,
    QWidget,
)


class SettingsPanel(QWidget):
    speed_changed = pyqtSignal(int)
    quality_changed = pyqtSignal(int)
    loop_changed = pyqtSignal(bool)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        speed_section = self._create_speed_section()
        layout.addWidget(speed_section)

        quality_section = self._create_quality_section()
        layout.addWidget(quality_section)

        extra_section = self._create_extra_section()
        layout.addWidget(extra_section)

        layout.addStretch()

    def _create_speed_section(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        label = QLabel("[ СКОРОСТЬ ]")
        label.setProperty("class", "info-text")
        layout.addWidget(label)

        slider_layout = QHBoxLayout()
        slider_layout.setSpacing(6)

        slow = QLabel("<<")
        slow.setProperty("class", "info-text")
        slider_layout.addWidget(slow)

        self._speed_slider = QSlider(Qt.Orientation.Horizontal)
        self._speed_slider.setMinimum(50)
        self._speed_slider.setMaximum(500)
        self._speed_slider.setValue(100)
        self._speed_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._speed_slider.setTickInterval(50)
        self._speed_slider.valueChanged.connect(self._on_speed_changed)
        slider_layout.addWidget(self._speed_slider)

        fast = QLabel(">>")
        fast.setProperty("class", "info-text")
        slider_layout.addWidget(fast)

        layout.addLayout(slider_layout)


        value_layout = QHBoxLayout()
        value_layout.addStretch()
        self._speed_value = QLabel("100ms")
        self._speed_value.setProperty("class", "value-display")
        value_layout.addWidget(self._speed_value)
        value_layout.addStretch()
        layout.addLayout(value_layout)

        return container

    def _create_quality_section(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        label = QLabel("[ КАЧЕСТВО ]")
        label.setProperty("class", "info-text")
        layout.addWidget(label)

        combo_layout = QHBoxLayout()
        combo_layout.setSpacing(6)

        combo_label = QLabel("уровень:")
        combo_label.setProperty("class", "info-text")
        combo_layout.addWidget(combo_label)

        self._quality_combo = QComboBox()
        self._quality_combo.addItems(["низкое", "среднее", "высокое"])
        self._quality_combo.setCurrentIndex(1)
        self._quality_combo.currentIndexChanged.connect(self._on_quality_changed)
        combo_layout.addWidget(self._quality_combo)

        layout.addLayout(combo_layout)

        info = QLabel("[* влияет на размер файла]")
        info.setProperty("class", "info-text")
        layout.addWidget(info)

        return container

    def _create_extra_section(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        label = QLabel("[ ЕЩЁ ]")
        label.setProperty("class", "info-text")
        layout.addWidget(label)

        self._loop_checkbox = QCheckBox("зациклить")
        self._loop_checkbox.setChecked(True)
        self._loop_checkbox.stateChanged.connect(
            lambda state: self.loop_changed.emit(state == 2)
        )
        layout.addWidget(self._loop_checkbox)

        return container

    def _on_speed_changed(self, value: int) -> None:
        self._speed_value.setText(f"{value}ms")
        self.speed_changed.emit(value)

    def _on_quality_changed(self, index: int) -> None:
        quality_values = [50, 75, 95]
        quality = quality_values[index] if index < len(quality_values) else 75
        self.quality_changed.emit(quality)

    def get_delay_ms(self) -> int:
        return self._speed_slider.value()

    def get_quality(self) -> int:
        index = self._quality_combo.currentIndex()
        quality_values = [50, 75, 95]
        return quality_values[index] if index < len(quality_values) else 75

    def is_looping(self) -> bool:
        return self._loop_checkbox.isChecked()

    def set_delay_ms(self, delay: int) -> None:
        self._speed_slider.setValue(delay)

    def set_quality(self, quality: int) -> None:
        quality_values = [50, 75, 95]
        if quality in quality_values:
            index = quality_values.index(quality)
            self._quality_combo.setCurrentIndex(index)

    def set_looping(self, looping: bool) -> None:
        self._loop_checkbox.setChecked(looping)
