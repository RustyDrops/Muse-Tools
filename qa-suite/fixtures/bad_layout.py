"""Known-bad layout fixture: turn-1 FAIL, locally fixable to PASS.

text_x sits far right so titles overflow; moving text_x left (widening
the column) fixes both title and body. Uses the pill tuple form
(pill_width, pill_height = 720, 58) from the handoff gotchas.
"""
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1080, 1350

cards = [
    ("LOCK THE TEMPLATE.", "Fixed size, fonts, and colors in code."),
    ("SHORT COPY WINS.", "Few words per card, nothing overflows."),
]

title_font = bold_font(34)
body_font = regular_font(28)
body_line_height = 39
text_x, text_width = 800, 240
card_height, gap = 190, 9
body_top = y + 66
pill_width, pill_height = 720, 58
pill_y = 1280

y = 273 + (index * (card_height + gap))
