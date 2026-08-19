# gif_creator.spec
#
# Файл конфигурации PyInstaller — описывает как собирать приложение.
# Использовать вместо длинных флагов командной строки: надёжнее и
# работает одинаково на всех платформах.
#
# Запуск: pyinstaller gif_creator.spec
#
# PyInstaller читает этот файл как обычный Python-скрипт,
# поэтому здесь можно использовать if/else, os.path и т.д.

import sys
import os
from pathlib import Path

# Корень проекта — папка где лежит этот .spec файл
project_root = Path(SPECPATH)  # SPECPATH — встроенная переменная PyInstaller

# ── Шаг 1: Analysis ────────────────────────────────────────────────────────
# PyInstaller анализирует импорты и собирает всё необходимое

a = Analysis(
    # Точка входа
    scripts=[str(project_root / 'main.py')],

    pathex=[str(project_root)],

    binaries=[],

    # Дополнительные файлы которые не импортируются, но нужны приложению.
    # Формат: ('откуда', 'куда внутри .exe')
    datas=[
        # CSS файл темы — без него приложение запустится без стилей
        (
            str(project_root / 'gui' / 'resources' / 'theme.qss'),
            'gui/resources'
        ),
        # Иконка приложения — используется в окне и таскбаре
        (
            str(project_root / 'gui' / 'resources' / 'icon.png'),
            'gui/resources'
        ),
    ],

    # hiddenimports — модули которые PyInstaller не видит через статический анализ.
    # numba и llvmlite используют динамические импорты внутри себя,
    # поэтому их нужно указать явно.
    hiddenimports=[
        'numba',
        'numba.core',
        'numba.core.typing',
        'numba.core.typing.cffi_utils',
        'llvmlite',
        'llvmlite.binding',
        # PyQt6 плагины для отображения изображений и шрифтов
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtMultimedia',
        # scipy может понадобиться если добавишь cKDTree
        'scipy.spatial',
        'scipy.spatial.cKDTree',
    ],

    # collect_all: собирает ВСЁ из указанного пакета включая data-файлы.
    # Для numba это критично — у неё есть .nbi и .nbc файлы кэша компиляции.
    collect_all=[
        'numba',
        'llvmlite',
    ],

    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],

    # excludes: пакеты которые точно не нужны — уменьшают размер файла
    excludes=[
        'tkinter',      # не используем tkinter
        'matplotlib',   # не используем
        'IPython',
        'jupyter',
        'pytest',
        'setuptools',
    ],

    noarchive=False,
    optimize=0,
)

# ── Шаг 2: PYZ ─────────────────────────────────────────────────────────────
# Упаковывает .pyc файлы в архив

pyz = PYZ(a.pure)

# ── Шаг 3: EXE ─────────────────────────────────────────────────────────────
# Создаёт исполняемый файл

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,


    name='FrameForge',
    debug=False,
    bootloader_ignore_signals=False,

    strip=False,

    upx=True,
    upx_exclude=[],

    runtime_tmpdir=None,

    console=False,
    disable_windowed_traceback=False,

    # target_arch — архитектура процессора. None = текущая.
    # Для macOS universal binary (Intel + Apple Silicon): 'universal2'
    target_arch=None,

    # codesign_identity — подпись кода для macOS (нужна для Gatekeeper)
    # None = без подписи (пользователи увидят предупреждение при первом запуске)
    codesign_identity=None,

    # entitlements_file — права приложения на macOS
    entitlements_file=None,

    icon=[str(project_root / 'gui' / 'resources' / 'icon.ico')] if sys.platform == 'win32' else None,
)
