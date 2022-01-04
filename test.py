from TileSet.Tile import Tile
from TileSet.Types import RGB

light: RGB = (161, 196, 240)
dark: RGB = (60, 65, 71)
darker: RGB = (27, 35, 43)

size = 32
for i in range(1, 2):
    tile = Tile((size, size), light, dark, darker, noise_scale=1, seed=i)
    tile.save(20)
    tile.add_top(size // 4)
    tile.save(20)
