from enum import Enum

from trimesh import Trimesh


class Color(Enum):
    """Enum for common colors used in Meshsee visualizations."""

    RED = (1.0, 0.0, 0.0)
    GREEN = (0.0, 1.0, 0.0)
    BLUE = (0.0, 0.0, 1.0)
    YELLOW = (1.0, 1.0, 0.0)
    CYAN = (0.0, 1.0, 1.0)
    MAGENTA = (1.0, 0.0, 1.0)
    ORANGE = (1.0, 0.65, 0.0)
    PURPLE = (0.5, 0.0, 0.5)
    PINK = (1.0, 0.75, 0.8)
    BROWN = (0.6, 0.4, 0.2)
    GRAY = (0.5, 0.5, 0.5)
    BLACK = (0.0, 0.0, 0.0)
    WHITE = (1.0, 1.0, 1.0)
    NAVY = (0.0, 0.0, 0.5)
    TEAL = (0.0, 0.5, 0.5)
    OLIVE = (0.5, 0.5, 0.0)
    MAROON = (0.5, 0.0, 0.0)
    LIME = (0.75, 1.0, 0.0)
    INDIGO = (0.29, 0.0, 0.51)
    TURQUOISE = (0.25, 0.88, 0.82)
    GOLD = (1.0, 0.84, 0.0)
    SILVER = (0.75, 0.75, 0.75)
    BEIGE = (0.96, 0.96, 0.86)
    CORAL = (1.0, 0.5, 0.31)
    SALMON = (0.98, 0.5, 0.45)
    CRIMSON = (0.86, 0.08, 0.24)
    KHAKI = (0.76, 0.69, 0.57)
    LAVENDER = (0.9, 0.9, 0.98)
    MINT = (0.74, 1.0, 0.79)
    SKY_BLUE = (0.53, 0.81, 0.92)


def set_mesh_color(
    mesh: Trimesh,
    color: tuple[float, float, float] | list[float] | Color,
    alpha: float = 1.0,
) -> Trimesh:
    """Set the color of a Trimesh object for Meshsee visualization.

    Args:
        mesh: The input mesh to which the color will be applied.
        color: The RGB color to set. Can be a tuple, list, or Color enum.
        alpha: The alpha transparency value for the color (0.0 to 1.0).

    Returns:
        Trimesh: The input mesh with updated color metadata.
    """
    if isinstance(color, Color):
        color = color.value
    for c in color:
        if not (0.0 <= c <= 1.0):
            raise ValueError("Color components must be in the range [0.0, 1.0]")
    if not (0.0 <= alpha <= 1.0):
        raise ValueError("Alpha value must be in the range [0.0, 1.0]")
    float_color = [float(c) for c in color]
    float_alpha = float(alpha)
    mesh.metadata["meshsee"] = {
        "color": [float_color[0], float_color[1], float_color[2], float_alpha]
    }
    return mesh
