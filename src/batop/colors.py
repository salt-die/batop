"""Default colors."""

from batgrl.colors import Color
from batgrl.text_tools import new_cell

FG_COLOR = Color.from_hex("f6a7a9")
BG_COLOR = Color.from_hex("070c25")
MIN_COLOR = Color.from_hex("1b244b")
MAX_COLOR = Color.from_hex("4d67ff")
DEFAULT_CELL = new_cell(fg_color=FG_COLOR, bg_color=BG_COLOR)
MENU_FG = Color.from_hex("fffffa")
MENU_NORMAL_BG = Color.from_hex("000000")
MENU_HOVER_BG = Color.from_hex("555555")
RED = Color.from_hex("9b2828")
GREEN = Color.from_hex("3fad08")
