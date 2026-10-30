# Standard Library
import json
import os
import re
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Any

# Third Party
import click

# Locals
from .generator import (
    ALL_DECORATIONS,
    encode_sheet,
    filter_combinations,
    valid_combinations,
)
from .tile import Tile
from .types import RGB, Decorations

CONFIG_NAME = "tileset.toml"


class HexColour(click.ParamType):
    name = "hex"

    def convert(
        self, value: str | RGB, param: click.Parameter | None, ctx: click.Context | None
    ) -> RGB:
        if isinstance(value, tuple):
            return value

        if match := re.fullmatch(r"#?([0-9a-fA-F]{6})", value):
            r, g, b = bytes.fromhex(match[1])
            return (r, g, b)

        self.fail(f"{value!r} is not a hex colour like #a1c4f0", param, ctx)


def tile_options(func: Callable) -> Callable:
    options = [
        click.option(
            "-o",
            "--output",
            type=click.Path(file_okay=False),
            default="tileset",
            help="Output directory.",
        ),
        click.option(
            "--size",
            type=click.IntRange(min=8),
            default=32,
            help="Tile width and height in pixels.",
        ),
        click.option(
            "--scale",
            type=click.IntRange(min=1),
            default=10,
            help="Upscale factor for individual tile images.",
        ),
        click.option("--seed", type=int, default=1, help="Noise seed."),
        click.option("--noise-scale", type=float, default=1.0, help="Noise frequency."),
        click.option(
            "--light", type=HexColour(), default="#8b5e3c", help="Lightest fill colour."
        ),
        click.option(
            "--dark",
            type=HexColour(),
            default="#4e3524",
            help="Darkest fill colour, lightest border colour.",
        ),
        click.option(
            "--darker",
            type=HexColour(),
            default="#2b1c13",
            help="Darkest border colour.",
        ),
        click.option(
            "--top-light",
            type=HexColour(),
            default="#7ec850",
            help="Lightest top colour.",
        ),
        click.option(
            "--top-dark",
            type=HexColour(),
            default="#4c9a32",
            help="Darkest top colour.",
        ),
    ]
    for option in reversed(options):
        func = option(func)

    return func


def make_tile(decorations: tuple[Decorations, ...], size: int, **options) -> Tile:
    tile = Tile((size, size), **options)
    tile.decorate(decorations)

    return tile


def find_config() -> Path | None:
    cwd = Path.cwd()
    for directory in [cwd, *cwd.parents]:
        if (path := directory / CONFIG_NAME).is_file():
            return path

    return None


def load_config(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as config_file:
            config = tomllib.load(config_file)
    except tomllib.TOMLDecodeError as error:
        raise click.ClickException(f"{path}: {error}") from error

    settings = {key.replace("-", "_"): value for key, value in config.items()}

    known = {param.name for param in generate.params}
    if unknown := sorted(settings.keys() - known):
        raise click.ClickException(f"{path}: unknown settings: {', '.join(unknown)}")

    if isinstance(settings.get("sheet_format"), str):
        settings["sheet_format"] = [settings["sheet_format"]]

    # Relative to the config file so results don't depend on where it's run from
    if "output" in settings:
        settings["output"] = str(path.parent / str(settings["output"]))

    return settings


@click.group(
    context_settings={"help_option_names": ["-h", "--help"], "show_default": True}
)
@click.version_option(package_name="tilesetgen")
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help=f"Settings file. Defaults to the nearest {CONFIG_NAME} in this directory or its parents.",
)
@click.pass_context
def cli(ctx: click.Context, config_path: Path | None) -> None:
    """Generate noise based tilesets.

    Command line options override settings from the config file.
    """
    config_path = config_path or find_config()
    if config_path is None:
        return

    click.echo(f"Using {config_path}", err=True)
    settings = load_config(config_path)
    ctx.default_map = {"generate": settings, "tile": settings}


@cli.command()
def init() -> None:
    """Write a config file with the default settings to this directory."""
    path = Path(CONFIG_NAME)
    if path.exists():
        raise click.ClickException(f"{path} already exists.")

    settings = [
        f"{param.name.replace('_', '-')} = {json.dumps(param.default)}"
        for param in generate.params
    ]
    path.write_text("\n".join(settings) + "\n")

    click.echo(path)


@cli.command()
@tile_options
@click.option(
    "--sheet-format",
    type=click.Choice(["png", "16bpp"]),
    multiple=True,
    default=["png"],
    help="Sheet file format, repeat for several. 16bpp is a 128x128 PicoSystem spritesheet.",
)
def generate(output: str, scale: int, sheet_format: tuple[str, ...], **options) -> None:
    """Generate every valid tile and combined sheets at native resolution."""
    tiles = [make_tile(combo, **options) for combo in valid_combinations()]

    try:
        sheets = {
            os.path.join(output, f"tileset.{name}"): encode_sheet(tiles, name)
            for name in sheet_format
        }
    except ValueError as error:
        raise click.UsageError(str(error)) from error

    for tile in tiles:
        tile.save(output, scale)

    os.makedirs(output, exist_ok=True)
    for path, data in sheets.items():
        Path(path).write_bytes(data)

    click.echo(f"Wrote {len(tiles)} tiles and {', '.join(sheets)}")


@cli.command()
@click.argument(
    "decorations", nargs=-1, type=click.Choice([d.name for d in ALL_DECORATIONS])
)
@tile_options
def tile(decorations: tuple[str, ...], output: str, scale: int, **options) -> None:
    """Generate a single tile with the given DECORATIONS, or a plain center tile with none."""
    combo = tuple(d for d in ALL_DECORATIONS if d.name in decorations)
    if not filter_combinations(combo):
        raise click.UsageError("A corner can't be combined with a side that covers it.")

    click.echo(make_tile(combo, **options).save(output, scale))
