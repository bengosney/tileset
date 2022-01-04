from TileSet.Corner import Corner
from TileSet.Side import Side
from TileSet.Tile import Tile
from TileSet.Types import RGB

light: RGB = (161, 196, 240)
dark: RGB = (60, 65, 71)
darker: RGB = (27, 35, 43)

size = 32
for i in range(1, 2):
    tile = Tile((size, size), light, dark, darker, noise_scale=1, seed=i)
    tile.save(20)
    tile.add_border(Side.left)
    tile.save(20)
    tile.add_corner(Corner.bottom_right)
    tile.save(20)
    tile.add_top()
    tile.save(20)
