import logging
from functools import cache

from matplotlib import font_manager, ft2font

logger = logging.getLogger(__name__)


@cache
def list_system_fonts(duplicate_regular: bool = True) -> dict[str, str]:
    """List system font you can use in text().

    Returns:
    A dict mapping font family names -> font file paths
    (only TrueType/OpenType fonts).
    """
    logger.info("Finding system fonts - this can take some time")
    # findSystemFonts returns absolute paths to .ttf/.otf files
    font_paths = font_manager.findSystemFonts(fontpaths=None, fontext="ttf")
    # also add OpenType fonts
    font_paths += font_manager.findSystemFonts(fontpaths=None, fontext="otf")
    fonts = {}
    for fp in font_paths:
        try:
            ft = ft2font.FT2Font(fp)
            fonts.setdefault(f"{ft.family_name}:style={ft.style_name}", fp)
            if duplicate_regular and ft.style_name == "Regular":
                # also add the font without style
                fonts.setdefault(f"{ft.family_name}", fp)
        except Exception:
            # corrupted font? skip
            continue
    if logger.isEnabledFor(logging.DEBUG):
        for font in sorted(fonts.keys()):
            logger.debug(f"Font: {font}")
    logger.info("Found system fonts")
    return fonts


def split_family_style(family_style: str) -> tuple[str, str]:
    if ":style=" in family_style:
        family, style = family_style.split(":style=", 1)
        return family, style
    else:
        return family_style, ""
