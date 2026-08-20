from __future__ import annotations

from collections.abc import Sequence

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QPushButton,
)


class SegmentedControl(QFrame):
    """Группа checkable-кнопок с взаимоисключающим выбором.

    Схож по поведению с QComboBox, но выглядит современнее.
    Первому элементу присваивается сегмент ``"first"``, последнему
    ``"last"`` для скругления краёв в QSS.
    """

    value_changed = pyqtSignal(int)  # индекс выбранной опции

    def __init__(self, options: Sequence[tuple[str, object]], parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("segmented")

        self._options = list(options)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        count = len(self._options)
        for index, (label, _data) in enumerate(self._options):
            button = QPushButton(label)
            button.setCheckable(True)
            button.setProperty("buttonStyle", "segment")
            button.setProperty("segment", _segment_role(index, count))
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _=False, i=index: self._on_clicked(i))
            layout.addWidget(button, stretch=1)
            self._group.addButton(button, index)
            setattr(self, f"_segment_{index}", button)

    # --- API -----------------------------------------------------------
    def set_current_index(self, index: int) -> None:
        button = self._group.button(index)
        if button is not None:
            button.setChecked(True)

    def set_current_data(self, data: object) -> None:
        for index, (_label, option_data) in enumerate(self._options):
            if option_data == data:
                self.set_current_index(index)
                return

    def current_index(self) -> int:
        checked = self._group.checkedButton()
        return self._group.id(checked) if checked is not None else 0

    def current_data(self) -> object:
        index = self.current_index()
        if 0 <= index < len(self._options):
            return self._options[index][1]
        return None

    # --- внутренняя логика ----------------------------------------------
    def _on_clicked(self, index: int) -> None:
        self.value_changed.emit(index)


def _segment_role(index: int, count: int) -> str:
    if index == 0:
        return "first"
    if index == count - 1:
        return "last"
    return "middle"