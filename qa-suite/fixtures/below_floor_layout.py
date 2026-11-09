"""Below-floor layout fixture: type under the floor AND unfixable.

Title/body sit below the 34/28 floor, so auto-fix must restore them to
the floor -- never pass them as-is. Even at the floor, the first title
is one unbreakable 90-character word: no text_x move can fit it, so the
verdict must be `unfixable` with exact px measurements attached.
"""
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1080, 1350

cards = [
    ("SUPERCALIFRAGILISTICEXPIALIDOCIOUSANTIDISESTABLISHMENTARIANISMENDS.",
     "Fixed size, fonts, and colors in code."),
    ("SHORT COPY WINS.", "Few words per card, nothing overflows."),
]

title_font = bold_font(34)
body_font = regular_font(28)
body_line_height = 34
text_x, text_width = 310, 730
card_height, gap = 190, 9
body_top = y + 66
pill_width, pill_height = 720, 58
pill_y = 1280

y = 273 + (index * (card_height + gap))
