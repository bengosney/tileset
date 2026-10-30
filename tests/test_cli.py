# Standard Library
from pathlib import Path

# Third Party
import pytest
from click.testing import CliRunner
from PIL import Image

# Locals
from tilesetgen.cli import cli
from tilesetgen.generator import valid_combinations


def run(*args: str | Path):
    return CliRunner().invoke(cli, [str(arg) for arg in args])


def test_generate_writes_every_tile_and_a_sheet(tmp_path: Path):
    result = run(
        "generate", "-o", tmp_path, "--size", "8", "--scale", "2", "--seed", "3"
    )

    assert result.exit_code == 0, result.output
    tile_count = len(list(valid_combinations()))
    assert len(list(tmp_path.glob("*.png"))) == tile_count + 1
    assert Image.open(tmp_path / "center_s3.png").size == (16, 16)
    assert Image.open(tmp_path / "tileset_s3.png").size[0] % 8 == 0


def test_tile_writes_one_named_tile(tmp_path: Path):
    result = run(
        "tile", "bottom_right", "left", "-o", tmp_path, "--size", "8", "--scale", "1"
    )

    assert result.exit_code == 0, result.output
    assert [path.name for path in tmp_path.iterdir()] == ["left-bottom_right_s1.png"]


def test_same_seed_is_reproducible_and_different_seed_is_not(tmp_path: Path):
    def render(seed: str, name: str) -> bytes:
        output = tmp_path / name
        run("tile", "top", "-o", output, "--size", "16", "--seed", seed)
        return next(output.iterdir()).read_bytes()

    assert render("1", "a") == render("1", "b")
    assert render("1", "c") != render("2", "d")


@pytest.mark.parametrize(
    "args",
    [
        ("tile", "top", "top_left"),
        ("tile", "middle"),
        ("tile", "--light", "blue"),
        ("tile", "--size", "4"),
    ],
)
def test_invalid_input_is_rejected(tmp_path: Path, args: tuple[str, ...]):
    result = run(*args, "-o", tmp_path)

    assert result.exit_code == 2
    assert list(tmp_path.iterdir()) == []
