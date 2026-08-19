import sys

from PyQt6.QtGui import QColor, QIcon, QPalette
from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow
from gui.resources import resource_path
from gui.resources.palette import BG, SURFACE, TEXT_PRIMARY


def _apply_light_palette(app: QApplication) -> None:
    """Светлая палитра приложения, чтобы фон никогда не был тёмным."""
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor(BG))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Base, QColor(SURFACE))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(BG))
    palette.setColor(QPalette.ColorRole.Text, QColor(TEXT_PRIMARY))
    app.setPalette(palette)


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    _apply_light_palette(app)

    icon_path = resource_path("icon.png")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()