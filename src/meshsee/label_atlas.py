from PIL import Image, ImageFont, ImageDraw

import moderngl
import numpy as np

import os

LABEL_CHARS = "0123456789-."
# MINUS_INDEX = LABEL_CHARS.index("-")
# DOT_INDEX = LABEL_CHARS.index(".")
FONT_SIZE = 100  # defines the resolution of the font
FONT_FILE = "DejaVuSansMono.ttf"
RELATIVE_PATH_TO_FONT = "."


def _load_font() -> ImageFont:
    font_path = os.path.join(
        os.path.dirname(__file__), RELATIVE_PATH_TO_FONT, FONT_FILE
    )
    return ImageFont.truetype(font_path, FONT_SIZE)


def _get_font_size(font: ImageFont) -> tuple:
    cell_bbox = font.getbbox("0")
    cell_height = cell_bbox[3]  # Height of a character cell
    cell_width = cell_bbox[2]  # Width of a character cell
    return (cell_width, cell_height)


class LabelAtlas:
    def __init__(self, ctx: moderngl.Context):
        self._create_label_atlas()
        self._texture = ctx.texture(
            (self._width, self._height),
            1,
            data=self._bytes,
            dtype="f1",
        )
        # self._texture.build_mipmaps()
        # self._texture.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
        self._sampler = ctx.sampler(texture=self._texture)
        self._sampler.filter = (ctx.NEAREST, ctx.NEAREST)

    def uv(self, char: str) -> np.ndarray:
        return self._uv_data[char]

    @property
    def image(self) -> Image:
        return self._image

    @property
    def texture(self) -> moderngl.Texture:
        return self._texture

    @property
    def sampler(self) -> moderngl.Sampler:
        return self._sampler

    def _create_label_atlas(self) -> tuple[np.ndarray, dict[str, np.ndarray]]:
        font = _load_font()
        self._cell_width, self._cell_height = _get_font_size(font)
        self._calc_atlas_size()
        self._draw_chars(LABEL_CHARS, font)
        self._uv_data = {
            char: np.array(uv, dtype="f4") for char, uv in self._uv_data.items()
        }
        self._bytes = self._image.tobytes()

    def _save_atlas(self) -> None:
        self._image.save("label_atlas.png")

    def _calc_atlas_size(self) -> tuple[int, int]:
        cols = len(LABEL_CHARS)
        self._width = cols * self._cell_width
        self._height = self._cell_height

    def _draw_chars(self, chars: str, font: ImageFont) -> None:
        # Create a new image for the atlas

        # Create a new image for the atlas
        self._image = Image.new("L", (self._width, self._height))
        draw = ImageDraw.Draw(self._image)

        # Draw each character into its cell
        self._uv_data = {}
        for i, char in enumerate(chars):
            self._draw_char(draw, font, char, i)

    def _draw_char(self, draw: ImageDraw, font, char: str, index: int) -> None:
        WHITE = 255
        x = index * self._cell_width
        draw.text((x, 0), char, fill=WHITE, font=font)
        # Save texture coordinates for later use (normalized coordinates)
        u0 = x / self._width
        v0 = 0.0
        u1 = (x + self._cell_width) / self._width
        v1 = 1.0
        self._uv_data[char] = (u0, v0, u1, v1)


if __name__ == "__main__":
    ctx = moderngl.create_standalone_context()
    label_atlas = LabelAtlas(ctx)
    print(label_atlas.get_uv("0"))
    print(label_atlas.get_uv("-"))
