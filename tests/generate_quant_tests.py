from pathlib import Path
from PIL import Image, ImageDraw


OUTPUT = Path(__file__).parent / "output"
OUTPUT.mkdir(exist_ok=True)
SIZE = (400, 300)

def gradient_horizontal():
    """Плавный горизонтальный градиент — проверяет постеризацию"""
    img = Image.new("RGB", SIZE)
    draw = ImageDraw.Draw(img)
    for x in range(SIZE[0]):
        r = int(x / SIZE[0] * 255)
        draw.line([(x, 0), (x, SIZE[1])], fill=(r, 30, 30))
    img.save(OUTPUT / "01_gradient_red.png")
    print("01_gradient_red.png — горизонтальный градиент")


def gradient_multi():
    """Многоцветный градиент — палитра распределяется между тонами"""
    img = Image.new("RGB", SIZE)
    draw = ImageDraw.Draw(img)
    for y in range(SIZE[1]):
        for x in range(SIZE[0]):
            r = int(x / SIZE[0] * 255)
            g = int(y / SIZE[1] * 255)
            b = 128
            img.putpixel((x, y), (r, g, b))
    img.save(OUTPUT / "02_gradient_multi.png")
    print("02_gradient_multi.png — многоцветный градиент")


def skin_tone():
    """Плавные переходы цвета кожи — критично для портретов"""
    img = Image.new("RGB", SIZE, (40, 30, 25))
    draw = ImageDraw.Draw(img)

    # Овал "лица" с градиентом
    for y in range(80, 220):
        for x in range(100, 300):
            # Расстояние от центра
            dx = (x - 200) / 100
            dy = (y - 150) / 70
            dist = (dx * dx + dy * dy) ** 0.5

            if dist < 1.0:
                # Цвет кожи с вариациями
                r = int(200 - dist * 40 + y * 0.1)
                g = int(150 - dist * 30 + y * 0.05)
                b = int(120 - dist * 20)
                img.putpixel((x, y), (r, g, b))

    img.save(OUTPUT / "03_skin_tone.png")
    print("03_skin_tone.png — оттенки кожи")


def shadows():
    """Тёмная сцена с тенями — проверяет сохранение деталей в тенях"""
    img = Image.new("RGB", SIZE, (5, 5, 8))
    draw = ImageDraw.Draw(img)

    # Несколько уровней теней
    for i in range(5):
        x0 = i * 80
        brightness = 10 + i * 8
        draw.rectangle(
            [x0, 50, x0 + 80, 250],
            fill=(brightness, brightness, brightness + 5)
        )

    # Мягкий переход
    for y in range(SIZE[1]):
        val = int(5 + y / SIZE[1] * 50)
        draw.line([(0, y), (SIZE[0], y)], fill=(val, val, val + 3))

    img.save(OUTPUT / "04_shadows.png")
    print("04_shadows.png — тени и тёмные тона")


def saturated_colors():
    """Яркие насыщенные цвета — проверяет распределение палитры"""
    img = Image.new("RGB", SIZE, (20, 20, 20))
    draw = ImageDraw.Draw(img)

    colors = [
        (255, 0, 0), (0, 255, 0), (0, 0, 255),
        (255, 255, 0), (255, 0, 255), (0, 255, 255),
        (255, 128, 0), (128, 0, 255),
    ]

    for i, color in enumerate(colors):
        x = 50 + (i % 4) * 90
        y = 50 + (i // 4) * 120
        draw.ellipse([x - 35, y - 35, x + 35, y + 35], fill=color)

    img.save(OUTPUT / "05_saturated.png")
    print("05_saturated.png — насыщенные цвета")


def fine_details():
    """Тонкие линии и текст — дизеринг может размыть"""
    img = Image.new("RGB", SIZE, (240, 240, 240))
    draw = ImageDraw.Draw(img)

    # Сетка тонких линий
    for i in range(0, SIZE[0], 10):
        draw.line([(i, 0), (i, SIZE[1])], fill=(100, 100, 100))
    for i in range(0, SIZE[1], 10):
        draw.line([(0, i), (SIZE[0], i)], fill=(100, 100, 100))

    # Текст
    try:
        draw.text((20, 20), "ABC abc 123", fill=(0, 0, 0))
        draw.text((20, 60), "Fine details", fill=(50, 50, 50))
    except:
        draw.rectangle([20, 20, 200, 40], fill=(0, 0, 0))
        draw.rectangle([20, 60, 250, 80], fill=(50, 50, 50))

    img.save(OUTPUT / "06_details.png")
    print("06_details.png — тонкие линии и детали")


def smooth_sphere():
    """3D-сфера с плавным освещением — классический тест рендеринга"""
    img = Image.new("RGB", SIZE, (30, 30, 40))

    cx, cy, r = 200, 150, 120

    for y in range(SIZE[1]):
        for x in range(SIZE[0]):
            dx = x - cx
            dy = y - cy
            dist = (dx * dx + dy * dy) ** 0.5

            if dist < r:
                # Нормаль для освещения
                nx = dx / r
                ny = dy / r
                nz = (1 - nx * nx - ny * ny) ** 0.5

                # Диффузное освещение
                light = max(0, nz * 0.7 + 0.3)

                red = int(200 * light)
                green = int(80 * light)
                blue = int(60 * light)

                img.putpixel((x, y), (red, green, blue))

    img.save(OUTPUT / "07_sphere.png")
    print("07_sphere.png — сфера с плавным освещением")


def color_bands():
    """Узкие полосы похожих цветов — проверяет дискриминацию близких тонов"""
    img = Image.new("RGB", SIZE)
    draw = ImageDraw.Draw(img)

    band_width = SIZE[0] // 20
    for i in range(20):
        x0 = i * band_width
        # Каждый следующий чуть-чуть отличается
        r = 100 + i * 3
        g = 150 + i * 2
        b = 200 - i * 2
        draw.rectangle([x0, 0, x0 + band_width, SIZE[1]], fill=(r, g, b))

    img.save(OUTPUT / "08_color_bands.png")
    print("08_color_bands.png — узкие полосы похожих цветов")


if __name__ == "__main__":
    gradient_horizontal()
    gradient_multi()
    skin_tone()
    shadows()
    saturated_colors()
    fine_details()
    smooth_sphere()
    color_bands()
    print(f"\nГотово! {8} тестов в {OUTPUT.absolute()}")