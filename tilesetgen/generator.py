# Standard Library
import math
from collections.abc import Iterable, Iterator
from io import BytesIO
from itertools import combinations, product

# Third Party
from PIL import Image

# Locals
from .corner import Corner
from .side import Side
from .tile import Tile
from .types import Decorations

ALL_DECORATIONS: list[Decorations] = [*Side, *Corner]

PICOSYSTEM_SPRITE_SIZE = 8
PICOSYSTEM_SHEET_SIZE = 128


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


def make_picosystem_sheet(tiles: list[Tile]) -> Image.Image:
    tile_size = tiles[0].size[0]
    if tile_size % PICOSYSTEM_SPRITE_SIZE:
        raise ValueError(
            f"PicoSystem sprites are on an {PICOSYSTEM_SPRITE_SIZE}px grid, "
            f"so the tile size must be a multiple of {PICOSYSTEM_SPRITE_SIZE}, not {tile_size}."
        )

    columns = PICOSYSTEM_SHEET_SIZE // tile_size
    if len(tiles) > columns**2:
        raise ValueError(
            f"{len(tiles)} tiles of {tile_size}px don't fit in a "
            f"{PICOSYSTEM_SHEET_SIZE}x{PICOSYSTEM_SHEET_SIZE} PicoSystem sheet, use a smaller tile size."
        )

    # Row by row, as sprite() counts its indexes left to right then down
    size = (PICOSYSTEM_SHEET_SIZE, PICOSYSTEM_SHEET_SIZE)
    sheet = Image.new("RGBA", size, (0, 0, 0, 0))
    for i, tile in enumerate(tiles):
        y, x = divmod(i, columns)
        sheet.paste(tile.image, (x * tile_size, y * tile_size))

    return sheet


def encode_16bpp(image: Image.Image) -> bytes:
    """Encode as big endian AAAARRRRGGGGBBBB, PicoSystem's Buffer format."""
    raw = image.convert("RGBA").tobytes()
    channels = zip(raw[0::4], raw[1::4], raw[2::4], raw[3::4])

    return bytes(
        byte
        for r, g, b, a in channels
        for byte in (a & 0xF0 | r >> 4, g & 0xF0 | b >> 4)
    )


def encode_sheet(tiles: list[Tile], sheet_format: str) -> bytes:
    if sheet_format == "16bpp":
        return encode_16bpp(make_picosystem_sheet(tiles))

    buffer = BytesIO()
    make_sheet(tiles).save(buffer, format="PNG")

    return buffer.getvalue()
