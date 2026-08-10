import random
import pytest

from core.median_cut import build_palette

@pytest.fixture
def random_image():
  random.seed(0)

  width = 30
  height = 20

  pixels_flat = [
    (
      random.randint(0, 255),
      random.randint(0, 255),
      random.randint(0, 255)
    )
    for _ in range(width * height)
  ]

  pixels_2d = [
    pixels_flat[y * width:(y + 1) * width]
    for y in range(height)
  ]

  palette = build_palette(pixels_flat, 16)

  return pixels_2d, palette