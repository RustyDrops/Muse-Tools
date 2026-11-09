"""Known-good layout fixture: passes check_layout as-is.

Auto-fix on this file must be a no-op (already passing, not rewritten).
Uses the variable body_top form (body_top = y + 66) from the handoff.
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
text_x, text_width = 315, 725
card_height, gap = 190, 9
body_top = y + 66
pill_width, pill_height = 720, 58
pill_y = 1280

y = 273 + (index * (card_height + gap))
