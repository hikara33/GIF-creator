from pathlib import Path
from PIL import Image, ImageDraw
import random

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def generate_50_colors_image():
    img = Image.new("RGB", (500, 500), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    unique_colors = set()

    # Рисуем квадратики, пока не наберем ровно 50 уникальных цветов (+ 1 черный фон = 51 цвет)
    while len(unique_colors) < 50:
        r = random.randint(20, 255)
        g = random.randint(20, 255)
        b = random.randint(20, 255)

        if (r, g, b) not in unique_colors:
            unique_colors.add((r, g, b))
            x = random.randint(0, 450)
            y = random.randint(0, 450)
            draw.rectangle([x, y, x + 50, y + 50], fill=(r, g, b))

    print(f"Сгенерирована картинка с {len(unique_colors) + 1} уникальными цветами (включая черный фон)")
    img.save(OUTPUT_DIR / "test_50_colors.png")


if __name__ == "__main__":
    generate_50_colors_image()