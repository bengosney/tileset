# Standard Library
import math
from collections.abc import Iterable, Iterator
from itertools import combinations, product

# Third Party
from PIL import Image

# Locals
from .corner import Corner
from .side import Side
from .tile import Tile
from .types import Decorations

ALL_DECORATIONS: list[Decorations] = [*Side, *Corner]


def filter_combinations(decorations: Iterable[Decorations]) -> bool:
    for decoration in decorations:
        if isinstance(decoration, Corner):
            if (
                decoration in [Corner.top_left, Corner.top_right]
                and Side.top in decorations
            ):
                return False
            if (
                decoration in [Corner.bottom_left, Corner.bottom_right]
                and Side.bottom in decorations
            ):
                return False
            if (
                decoration in [Corner.top_left, Corner.bottom_left]
                and Side.left in decorations
            ):
                return False
            if (
                decoration in [Corner.top_right, Corner.bottom_right]
                and Side.right in decorations
            ):
                return False

    return True


def valid_combinations() -> Iterator[tuple[Decorations, ...]]:
    for size in range(len(ALL_DECORATIONS) + 1):
        yield from filter(filter_combinations, combinations(ALL_DECORATIONS, size))


def make_sheet(tiles: list[Tile]) -> Image.Image:
    tile_width, tile_height = tiles[0].size
    row_cols = math.ceil(math.sqrt(len(tiles)))

    sheet = Image.new(
        "RGBA", (tile_width * row_cols, tile_height * row_cols), (0, 0, 0, 0)
    )
    for tile, (x, y) in zip(tiles, product(range(row_cols), repeat=2)):
        sheet.paste(tile.image, (x * tile_width, y * tile_height))

    return sheet
