# Standard Library
import math
from typing import Iterator

# Third Party
from opensimplex import OpenSimplex

# Locals
from .Types import RGB, Number, Point, Range


def remap(x: Number, from_range: Range, to_range: Range) -> Number:
    from_min, from_max = from_range
    to_min, to_max = to_range
    return (x - from_min) * (to_max - to_min) / (from_max - from_min) + to_min


def get_colour(value: Number, dark: RGB, light: RGB) -> RGB:
    r = remap(value, (-1, 1), (dark[0], light[0]))
    g = remap(value, (-1, 1), (dark[1], light[1]))
    b = remap(value, (-1, 1), (dark[2], light[2]))

    return (int(r), int(g), int(b))


def points_on_circle(radius: int, points: int) -> Iterator[Point]:
    for x in range(points + 1):
        p = 2 * math.pi / points * x
        yield (int(math.cos(p) * radius), int(math.sin(p) * radius))


def get_wave(size: int, noise: OpenSimplex, scale: Range) -> Iterator[Number]:
    for x, y in points_on_circle(size, size):
        yield remap(noise.noise2(x, y), (-1, 1), scale)
