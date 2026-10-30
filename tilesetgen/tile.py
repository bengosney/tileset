# Standard Library
import os
from collections.abc import Iterable

# Third Party
# import opensimplex
from opensimplex import OpenSimplex
from PIL import Image

# Locals
from .corner import Corner
from .side import Side
from .types import RGB, Decorations, Number, Size
from .utils import get_colour, get_wave


class Tile:
    def __init__(
        self,
        size: Size,
        light: RGB,
        dark: RGB,
        darker: RGB,
        noise_scale: float = 1,
        seed: int = 1,
        sand_light: RGB = (194, 178, 128),
        sand_dark: RGB = (174, 160, 115),
    ):
        self.image: Image.Image = Image.new("RGBA", size, (0, 0, 0, 0))
        self.size: Size = size
        self.decoration_size: int = size[0] // 8
        self.noise_scale: float = noise_scale

        self.light: RGB = light
        self.dark: RGB = dark
        self.darker: RGB = darker
        self.sand_light: RGB = sand_light
        self.sand_dark: RGB = sand_dark

        self.noise: OpenSimplex = OpenSimplex(seed)

        self.decorations: list[Decorations] = []

        self._fill()

    def _get_noise(self, x: int, y: int) -> Number:
        return self.noise.noise2(x * self.noise_scale, y * self.noise_scale)

    def _fill(self):
        for x in range(self.size[0]):
            for y in range(self.size[1]):
                value = self._get_noise(x, y)
                self.image.putpixel((x, y), get_colour(value, self.dark, self.light))

    def add_corner(self, corner: Corner) -> None:
        self.decorations.append(corner)
        tmp = self.image.rotate(corner.value)

        for x in range(self.decoration_size):
            for y in range(self.decoration_size):
                value = self._get_noise(x, y)
                tmp.putpixel((x, y), get_colour(value, self.darker, self.dark))

        self.image = tmp.rotate(-corner.value)

    def add_border(self, side: Side) -> None:
        self.decorations.append(side)
        tmp = self.image.rotate(side.value)

        for x in range(self.size[0]):
            for y in range(self.decoration_size):
                value = self._get_noise(x, y)
                tmp.putpixel((x, y), get_colour(value, self.darker, self.dark))

        self.image = tmp.rotate(-side.value)

    def add_top(self) -> None:
        self.decorations.append(Side.top)
        size = self.decoration_size * 2

        wave = list(get_wave(self.size[0], self.noise, (0, size)))
        for x in range(self.size[0]):
            max_y = int(wave[x]) + size // 2
            for y in range(max_y):
                value = self._get_noise(x, y)
                self.image.putpixel(
                    (x, y), get_colour(value, self.sand_dark, self.sand_light)
                )

    def decorate(self, decorations: Iterable[Decorations]) -> None:
        decorations = list(decorations)
        for decoration in decorations:
            if isinstance(decoration, Corner):
                self.add_corner(decoration)
            elif decoration != Side.top:
                self.add_border(decoration)

        # The top is drawn last so it sits over the other decorations
        if Side.top in decorations:
            self.add_top()

        self.decorations = decorations

    @property
    def name(self) -> str:
        if len(self.decorations) == 0:
            return "center"

        return "-".join(d.name for d in self.decorations)

    def save(self, output: str = "tiles", scale: int = 1) -> str:
        os.makedirs(output, exist_ok=True)
        path = os.path.join(output, f"{self.name}.png")
        size = (self.size[0] * scale, self.size[1] * scale)
        self.image.resize(size, Image.NEAREST).save(path)

        return path
