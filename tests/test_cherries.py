from pathlib import Path
from PIL import Image, ImageDraw

from core.median_cut import build_palette
from core.floyd_steinberg import apply_dithering

from utils.metrics import compare_quality

TEST_DIR = Path(__file__).parent / "output"
RESULT_DIR = Path(__file__).parent / "results"
RESULT_DIR.mkdir(exist_ok=True)

# Сравниваем три размера, как вы и хотели в предыдущем вопросе
PALETTE_SIZES = [64, 128, 256]


def test_image(image_path: Path) -> None:
    print(f"Обрабатываю: {image_path.name} ...", end=" ")

    orig = Image.open(image_path).convert("RGB")
    pixels_2d = [
        [orig.getpixel((x, y)) for x in range(orig.width)]
        for y in range(orig.height)
    ]

    # Вытягиваем все пиксели для построения палитры
    all_pixels = [p for row in pixels_2d for p in row]

    for palette_size in PALETTE_SIZES:
        # 1. Строим палитру (твой алгоритм)
        palette = build_palette(all_pixels, palette_size=palette_size)

        # 2. Квантизуем с дизерингом (твой алгоритм)
        indexed_2d = apply_dithering(pixels_2d, palette)

        metrics = compare_quality(pixels_2d, indexed_2d, palette)
        print(f"  palette={palette_size}: MSE={metrics['mse']:.2f}, PSNR={metrics['psnr']:.1f} дБ")

        # 3. Собираем результат обратно в картинку
        result = Image.new("RGB", orig.size)
        for y in range(orig.height):
            for x in range(orig.width):
                idx = indexed_2d[y][x]
                result.putpixel((x, y), palette[idx])

        # 4. Склеиваем оригинал и результат рядом (side-by-side)
        comparison = Image.new("RGB", (orig.width * 2 + 20, orig.height + 40), (40, 40, 40))
        comparison.paste(orig, (0, 30))
        comparison.paste(result, (orig.width + 20, 30))

        draw = ImageDraw.Draw(comparison)
        draw.text((5, 5), "ORIGINAL", fill=(200, 200, 200))
        draw.text((orig.width + 25, 5), f"MY ALG (pal={palette_size})", fill=(200, 200, 200))

        out_path = RESULT_DIR / f"{image_path.stem}_pal{palette_size}.png"
        comparison.save(out_path)

    print("Готово!")


def main() -> None:
    # Задаем имя конкретного файла
    target_filename = "cherry-heart.jpg"
    image_path = TEST_DIR / target_filename

    # Проверяем, существует ли файл
    if not image_path.exists():
        print(f"ОШИБКА: Файл {target_filename} не найден в папке {TEST_DIR}")
        return

    print(f"Запуск теста для одной картинки:\n")
    test_image(image_path)

    print(f"\n========================================")
    print(f"ВСЁ! Открой папку и смотри результаты:")
    print(f"{RESULT_DIR.absolute()}")
    print(f"========================================")


if __name__ == "__main__":
    main()