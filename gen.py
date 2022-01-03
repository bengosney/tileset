# Standard Library
import math
import os
from enum import Enum
from itertools import combinations, product
from typing import Iterable, Iterator

# Third Party
import opensimplex
from PIL import Image

Number = int | float
Range = tuple[Number, Number]
Size = tuple[int, int]
Point = tuple[int, int]
RGB = tuple[int, int, int]

tile_size: Size = (32, 32)
light: RGB = (161, 196, 240)
dark: RGB = (60, 65, 71)
darker: RGB = (27, 35, 43)
seed: int = 1
base_noise_scale: int = 1
output_scale: int = 10


def points_on_circle(radius: int, points: int) -> Iterator[Point]:
    for x in range(points + 1):
        p = 2 * math.pi / points * x
        yield (int(math.cos(p) * radius), int(math.sin(p) * radius))


def remap(x: Number, from_range: Range, to_range: Range) -> Number:
    from_min, from_max = from_range
    to_min, to_max = to_range
    return (x - from_min) * (to_max - to_min) / (from_max - from_min) + to_min


def get_wave(size: int, scale: Range) -> Iterator[Number]:
    for x, y in points_on_circle(size, size):
        yield remap(opensimplex.noise2(x, y), (-1, 1), scale)


def get_colour(value: Number, dark: RGB, light: RGB) -> RGB:
    r = remap(value, (-1, 1), (dark[0], light[0]))
    g = remap(value, (-1, 1), (dark[1], light[1]))
    b = remap(value, (-1, 1), (dark[2], light[2]))

    return (int(r), int(g), int(b))


def save(image: Image.Image, name: str) -> None:
    os.makedirs("tileset", exist_ok=True)
    size = (tile_size[0] * output_scale, tile_size[1] * output_scale)
    image.resize(size, Image.NEAREST).save(os.path.join("tileset", f"{name}.png"))


def reseed():
    global seed
    seed += 1
    opensimplex.seed(seed)


reseed()

base = Image.new("RGB", tile_size)

for x in range(tile_size[0]):
    for y in range(tile_size[1]):
        value = opensimplex.noise2(x * base_noise_scale, y * base_noise_scale)
        base.putpixel((x, y), get_colour(value, dark, light))


save(base, "center")


class Side(Enum):
    top = 0
    left = -90
    right = 90
    bottom = 180


class Corner(Enum):
    top_left = 0
    top_right = 90
    bottom_right = 180
    bottom_left = 270


def add_corner(image: Image.Image, size: int, corner: Corner) -> Image.Image:
    tmp = image.rotate(corner.value)

    for x in range(size):
        for y in range(size):
            value = opensimplex.noise2(x * base_noise_scale, y * base_noise_scale)
            tmp.putpixel((x, y), get_colour(value, darker, dark))

    return tmp.rotate(-corner.value)


def add_border(image: Image.Image, size: int, side: Side) -> Image.Image:
    tmp = image.rotate(side.value)

    for x in range(tile_size[0]):
        for y in range(size):
            value = opensimplex.noise2(x * base_noise_scale, y * base_noise_scale)
            tmp.putpixel((x, y), get_colour(value, darker, dark))

    return tmp.rotate(-side.value)


def add_top(image: Image.Image, size: int) -> Image.Image:
    sand_light = (194, 178, 128)
    sand_dark = (174, 160, 115)

    wave = list(get_wave(tile_size[0], (0, size)))
    for x in range(tile_size[0]):
        max_y = int(wave[x]) + size // 2
        for y in range(max_y):
            value = opensimplex.noise2(x * base_noise_scale, y * base_noise_scale)
            image.putpixel((x, y), get_colour(value, sand_dark, sand_light))

    return image


def filter_combinations(decorations: Iterable[Side | Corner]) -> bool:
    for decoration in decorations:
        if isinstance(decoration, Corner):
            if decoration in [Corner.top_left, Corner.top_right] and Side.top in decorations:
                return False
            if decoration in [Corner.bottom_left, Corner.bottom_right] and Side.bottom in decorations:
                return False
            if decoration in [Corner.top_left, Corner.bottom_left] and Side.left in decorations:
                return False
            if decoration in [Corner.top_right, Corner.bottom_right] and Side.right in decorations:
                return False

    return True


def add_decoration(image: Image.Image, decorations: Iterable[Side | Corner]) -> Image.Image:
    size = tile_size[0] // 8
    for decoration in decorations:
        if isinstance(decoration, Side):
            if decoration != Side.top:
                image = add_border(image, size, decoration)
        else:
            image = add_corner(image, size, decoration)

    if Side.top in decorations:
        image = add_top(image, tile_size[0] // 4)

    return image


all_decorations: list[Side | Corner] = [*Side, *Corner]
tileset: list[Image.Image] = [base]
for size in range(1, len(all_decorations) + 1):
    for combo in combinations(all_decorations, size):
        if filter_combinations(combo):
            name = "-".join(str(side).split(".")[-1] for side in combo)
            img = add_decoration(base.copy(), combo)
            tileset.append(img)
            save(img, name)


row_cols = math.ceil(math.sqrt(len(tileset)))
sheet_size: Size = (tile_size[0] * row_cols, tile_size[1] * row_cols)

sheet = Image.new("RGBA", sheet_size, (0, 0, 0, 0))
for i, (x, y) in enumerate(product(range(row_cols), repeat=2)):
    dest = (x * tile_size[0], y * tile_size[1])
    try:
        img = tileset[i]
        sheet.paste(img, dest)
    except IndexError:
        break

sheet.resize(sheet_size, Image.NEAREST).save(os.path.join("tileset", "tileset.png"))
