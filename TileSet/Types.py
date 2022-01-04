# Locals
from .Corner import Corner
from .Side import Side

Size = tuple[int, int]
RGB = tuple[int, int, int]
Number = int | float
Range = tuple[Number, Number]
Point = tuple[int, int]
Decorations = Corner | Side
