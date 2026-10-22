from PIL import Image, ImageDraw, ImageFont

BACKGROUND = (170, 170, 170)  # Kickstart 1.3 grey
FLOPPY = (0, 0, 0)
LABEL = (255, 255, 255)
TEXT = (0, 85, 170)
LINES = ("Insert disk", "Select a game in the list")


class AmigaScreen:
    """Draws a Kickstart-style 'insert disk' screen, used when no game is selected."""

    @staticmethod
    def _font(size):
        for name in ("Menlo.ttc", "Courier New Bold.ttf", "couri.ttf", "DejaVuSansMono-Bold.ttf",
                     "Courier New.ttf"):
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                continue
        return ImageFont.load_default(size=size)

    @classmethod
    def render(cls, size):
        """Return an RGB image of exactly `size` (width, height)."""
        w, h = size
        img = Image.new("RGB", size, BACKGROUND)
        draw = ImageDraw.Draw(img)
        # a 3.5" disk: black body with a metal shutter and a white label
        dw = int(min(w * 0.4, h * 0.5))
        x0, y0 = (w - dw) // 2, int(h * 0.12)
        draw.rectangle((x0, y0, x0 + dw, y0 + dw), fill=FLOPPY)
        draw.rectangle((x0 + dw * 0.2, y0, x0 + dw * 0.8, y0 + dw * 0.32), fill=BACKGROUND)
        draw.rectangle((x0 + dw * 0.62, y0 + dw * 0.05, x0 + dw * 0.72, y0 + dw * 0.27), fill=FLOPPY)
        draw.rectangle((x0 + dw * 0.12, y0 + dw * 0.52, x0 + dw * 0.88, y0 + dw * 0.95), fill=LABEL)
        font = cls._font(max(8, int(h / 14)))
        y = y0 + dw + int(h * 0.07)
        for line in LINES:
            width = draw.textlength(line, font=font)
            draw.text(((w - width) / 2, y), line, font=font, fill=TEXT)
            y += font.getbbox("Mg")[3] * 1.5
        return img
