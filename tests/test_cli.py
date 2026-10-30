# Standard Library
from pathlib import Path

# Third Party
import pytest
from click.testing import CliRunner
from PIL import Image

# Locals
from tilesetgen.cli import cli
from tilesetgen.generator import encode_16bpp, valid_combinations


@pytest.fixture(autouse=True)
def in_tmp_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)


def run(*args: str | Path):
    return CliRunner().invoke(cli, [str(arg) for arg in args])


def write_config(directory: Path, name: str = "tileset.toml", **settings) -> Path:
    path = directory / name
    lines = [f"{key.replace('_', '-')} = {value!r}" for key, value in settings.items()]
    path.write_text("\n".join(lines) + "\n")
    return path


def test_generate_writes_every_tile_and_a_sheet(tmp_path: Path):
    result = run(
        "generate", "-o", tmp_path, "--size", "8", "--scale", "2", "--seed", "3"
    )

    assert result.exit_code == 0, result.output
    tile_count = len(list(valid_combinations()))
    assert len(list(tmp_path.glob("*.png"))) == tile_count + 1
    assert Image.open(tmp_path / "center.png").size == (16, 16)
    assert Image.open(tmp_path / "tileset.png").size[0] % 8 == 0


def test_tile_writes_one_named_tile(tmp_path: Path):
    result = run(
        "tile", "bottom_right", "left", "-o", tmp_path, "--size", "8", "--scale", "1"
    )

    assert result.exit_code == 0, result.output
    assert [path.name for path in tmp_path.iterdir()] == ["left-bottom_right.png"]


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


def test_config_settings_are_used(tmp_path: Path):
    write_config(tmp_path, size=8, scale=1, seed=7, output="out", noise_scale=0.5)

    result = run("tile")

    assert result.exit_code == 0, result.output
    assert Image.open(tmp_path / "out" / "center.png").size == (8, 8)


def test_config_gives_the_same_tile_as_the_equivalent_options(tmp_path: Path):
    write_config(
        tmp_path, size=16, seed=4, noise_scale=0.25, light="#ff0000", output="a"
    )

    assert run("tile", "top").exit_code == 0
    run(
        "--config",
        write_config(tmp_path, "empty.toml"),
        "tile",
        "top",
        "--size",
        "16",
        "--seed",
        "4",
        "--noise-scale",
        "0.25",
        "--light",
        "#ff0000",
        "-o",
        "b",
    )

    name = "top.png"
    assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()


def test_options_override_config(tmp_path: Path):
    write_config(tmp_path, size=8, scale=1, seed=7, output="out")

    path = tmp_path / "out" / "center.png"

    result = run("tile", "--seed", "9", "--scale", "2")

    assert result.exit_code == 0, result.output
    assert Image.open(path).size == (16, 16)
    overridden = path.read_bytes()

    assert run("tile", "--scale", "2").exit_code == 0
    assert path.read_bytes() != overridden


def test_config_is_found_in_parents_and_output_is_relative_to_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    write_config(tmp_path, size=8, scale=1, output="out")
    nested = tmp_path / "some" / "nested"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)

    result = run("tile")

    assert result.exit_code == 0, result.output
    assert (tmp_path / "out" / "center.png").exists()
    assert list(nested.iterdir()) == []


def test_config_option_selects_a_file(tmp_path: Path):
    write_config(tmp_path, size=8, seed=1, output="ignored")
    other = write_config(tmp_path, "other.toml", size=8, seed=2, output="used")

    result = run("--config", other, "tile")

    assert result.exit_code == 0, result.output
    assert (tmp_path / "used" / "center.png").exists()
    assert not (tmp_path / "ignored").exists()


@pytest.mark.parametrize(
    "content, exit_code, message",
    [
        ("sede = 1\n", 1, "sede"),
        ("size = [\n", 1, "tileset.toml"),
        ('size = "big"\n', 2, "--size"),
        ('light = "blue"\n', 2, "--light"),
    ],
)
def test_bad_config_is_rejected(
    tmp_path: Path, content: str, exit_code: int, message: str
):
    (tmp_path / "tileset.toml").write_text(content)

    result = run("tile", "-o", "out")

    assert result.exit_code == exit_code
    assert message in result.output
    assert not (tmp_path / "out").exists()


def test_missing_config_option_is_rejected():
    assert run("--config", "nope.toml", "tile").exit_code == 2


def test_init_writes_the_defaults(tmp_path: Path):
    assert run("tile", "top", "-o", "defaults").exit_code == 0

    assert run("init").exit_code == 0
    config = (tmp_path / "tileset.toml").read_text()
    assert "noise-scale = 1.0" in config
    assert 'output = "tileset"' in config

    assert run("tile", "top").exit_code == 0
    name = "top.png"
    assert (tmp_path / "tileset" / name).read_bytes() == (
        tmp_path / "defaults" / name
    ).read_bytes()


def test_init_does_not_overwrite(tmp_path: Path):
    config = write_config(tmp_path, seed=5)

    assert run("init").exit_code == 1
    assert config.read_text() == "seed = 5\n"


def test_encode_16bpp_is_big_endian_argb4444():
    image = Image.new("RGBA", (2, 1))
    image.putpixel((0, 0), (0x4A, 0x8B, 0x2C, 0xFF))
    image.putpixel((1, 0), (0x12, 0x34, 0x56, 0x00))

    assert encode_16bpp(image) == bytes([0xF4, 0x82, 0x01, 0x35])


def test_16bpp_sheet_matches_picosystem_layout(tmp_path: Path):
    result = run("generate", "-o", tmp_path, "--size", "8", "--sheet-format", "16bpp")

    assert result.exit_code == 0, result.output
    data = (tmp_path / "tileset.16bpp").read_bytes()
    assert len(data) == 128 * 128 * 2
    assert not (tmp_path / "tileset.png").exists()

    tile_count = len(list(valid_combinations()))
    columns = 128 // 8
    last_row, last_column = divmod(tile_count - 1, columns)

    def pixel(x: int, y: int) -> bytes:
        return data[(y * 128 + x) * 2 : (y * 128 + x) * 2 + 2]

    # The last tile is opaque, and everything after it is transparent padding
    assert pixel(last_column * 8, last_row * 8)[0] >> 4 == 0xF
    assert pixel((last_column + 1) * 8, last_row * 8) == b"\x00\x00"
    assert pixel(127, 127) == b"\x00\x00"


@pytest.mark.parametrize("size, message", [("32", "fit"), ("12", "multiple")])
def test_16bpp_sheet_rejects_sizes_it_cannot_hold(
    tmp_path: Path, size: str, message: str
):
    result = run("generate", "-o", tmp_path, "--size", size, "--sheet-format", "16bpp")

    assert result.exit_code == 2
    assert message in result.output
    assert list(tmp_path.iterdir()) == []


def test_sheet_format_can_be_set_in_config(tmp_path: Path):
    write_config(tmp_path, size=16, sheet_format="16bpp", output="out")

    assert run("generate").exit_code == 0
    assert (tmp_path / "out" / "tileset.16bpp").stat().st_size == 128 * 128 * 2
    assert run("tile").exit_code == 0


def test_generate_can_write_both_sheet_formats(tmp_path: Path):
    both = tmp_path / "both"
    single = tmp_path / "single"

    result = run(
        "generate",
        "-o",
        both,
        "--size",
        "16",
        "--sheet-format",
        "png",
        "--sheet-format",
        "16bpp",
    )

    assert result.exit_code == 0, result.output
    assert run("generate", "-o", single, "--size", "16").exit_code == 0
    assert (both / "tileset.png").read_bytes() == (single / "tileset.png").read_bytes()
    assert (both / "tileset.16bpp").stat().st_size == 128 * 128 * 2


def test_both_sheet_formats_can_be_set_in_config(tmp_path: Path):
    write_config(tmp_path, size=16, sheet_format=["png", "16bpp"], output="out")

    assert run("generate").exit_code == 0
    assert (tmp_path / "out" / "tileset.png").exists()
    assert (tmp_path / "out" / "tileset.16bpp").exists()


def test_no_sheets_are_written_if_one_format_cannot_hold_the_tiles(tmp_path: Path):
    result = run(
        "generate", "-o", tmp_path, "--sheet-format", "png", "--sheet-format", "16bpp"
    )

    assert result.exit_code == 2
    assert list(tmp_path.iterdir()) == []
