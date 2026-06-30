from pathlib import Path


def load_pixel_theme() -> str:
    current_dir = Path(__file__).parent
    css_file = current_dir / "pixel_theme.css"
    
    if not css_file.exists():
        raise FileNotFoundError(f"CSS файл не найден: {css_file}")
    
    with open(css_file, 'r', encoding='utf-8') as f:
        return f.read()


PIXEL_THEME_STYLESHEET = load_pixel_theme()
