import logging
import os
from functools import cache

from matplotlib import font_manager, ft2font

logger = logging.getLogger(__name__)

DEFAULT_FONT = "DejaVu Sans Mono:style=Book"  # Default font to use if not specified
RELATIVE_PATH_TO_FONT = "./resources/"
FONT_FILE = "DejaVuSansMono.ttf"  # Default font file name
DEFAULT_FONT_PATH = os.path.join(
    os.path.dirname(__file__), RELATIVE_PATH_TO_FONT, FONT_FILE
)


@cache
def list_system_fonts(duplicate_regular: bool = True) -> dict[str, str]:
    """List system font you can use in text().

    Returns:
    A dict mapping font family names -> font file paths
    (only TrueType/OpenType fonts).
    """
    logger.info("Finding system fonts - this can take some time")
    font_paths = [DEFAULT_FONT_PATH]
    # findSystemFonts returns absolute paths to .ttf/.otf files
    font_paths += font_manager.findSystemFonts(fontpaths=None, fontext="ttf")
    # also add OpenType fonts
    font_paths += font_manager.findSystemFonts(fontpaths=None, fontext="otf")
    fonts: dict[str, str] = {}
    for fp in font_paths:
        try:
            ft = ft2font.FT2Font(fp)
            fonts.setdefault(f"{ft.family_name}:style={ft.style_name}", fp)
            if duplicate_regular and ft.style_name == "Regular":
                # also add the font without style
                fonts.setdefault(f"{ft.family_name}", fp)
        except Exception as e:
            # corrupted font? skip
            logger.debug(f"Exception for font path {fp}: {e}")
            continue
    if logger.isEnabledFor(logging.DEBUG):
        for font in sorted(fonts.keys()):
            logger.debug(f"Font: {font}")
    logger.info(f"Found {len(fonts)} fonts")
    return fonts


def split_family_style(family_style: str) -> tuple[str, str]:
    if ":style=" in family_style:
        family, style = family_style.split(":style=", 1)
        return family, style
    else:
        return family_style, ""
