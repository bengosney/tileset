# Standard Library
import os

# Third Party
# import opensimplex
from opensimplex import OpenSimplex
from PIL import Image

# Locals
from .Corner import Corner
from .Side import Side
from .Types import RGB, Decorations, Number, Size
from .Utils import get_colour, get_wave


class Tile:
    def __init__(self, size: Size, light: RGB, dark: RGB, darker: RGB, noise_scale: float = 1, seed: int = 1):
        self.image: Image.Image = Image.new("RGBA", size, (0, 0, 0, 0))
        self.size: Size = size
        self.decoration_size: int = size[0] // 4
        self.noise_scale: float = noise_scale

        self.light: RGB = light
        self.dark: RGB = dark
        self.darker: RGB = darker

        self.noise: OpenSimplex = OpenSimplex(seed)
        self.seed: int = seed

        self.decorations: list[Decorations] = []

        self._fill()

    def _get_noise(self, x: int, y: int) -> Number:
        return self.noise.noise2(x * self.noise_scale, y * self.noise_scale)

    def _fill(self):
        for x in range(self.size[0]):
            for y in range(self.size[1]):
                value = self._get_noise(x, y)
                self.image.putpixel((x, y), get_colour(value, self.dark, self.light))

    def add_corner(self, corner: Corner) -> Image.Image:
        self.decorations.append(corner)
        tmp = self.image.rotate(corner.value)

        for x in range(self.decoration_size):
            for y in range(self.decoration_size):
                value = self._get_noise(x, y)
                tmp.putpixel((x, y), get_colour(value, self.darker, self.dark))

        return tmp.rotate(-corner.value)

    def add_border(self, image: Image.Image, size: int, side: Side) -> Image.Image:
        self.decorations.append(side)
        tmp = image.rotate(side.value)

        for x in range(self.size[0]):
            for y in range(self.decoration_size):
                value = self._get_noise(x, y)
                tmp.putpixel((x, y), get_colour(value, self.darker, self.dark))

        return tmp.rotate(-side.value)

    def add_top(self, size: int) -> None:
        self.decorations.append(Side.top)
        sand_light = (194, 178, 128)
        sand_dark = (174, 160, 115)

        wave = list(get_wave(self.size[0], self.noise, (0, size)))
        for x in range(self.size[0]):
            max_y = int(wave[x]) + size // 2
            for y in range(max_y):
                value = self._get_noise(x, y)
                self.image.putpixel((x, y), get_colour(value, sand_dark, sand_light))

    @property
    def name(self) -> str:
        if len(self.decorations) == 0:
            name = "center"
        else:
            name = "-".join(d.name for d in self.decorations)

        return f"{name}_s{self.seed}"

    def save(self, scale: int = 1) -> None:
        path = os.path.join("tiles")
        os.makedirs(path, exist_ok=True)
        size = (self.size[0] * scale, self.size[1] * scale)
        self.image.resize(size, Image.NEAREST).save(os.path.realpath(os.path.join(path, f"{self.name}.png")))
