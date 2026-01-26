# Importing the modules takes time the first run, so we use lazy loading
# to speed up the initial import of scadview.

# This is so the the documetation tools can see these symbols
if False:
    from scadview.api.colors import (
        Color,
        set_mesh_color,
    )
    from scadview.api.linear_extrude import (
        ProfileType,
        linear_extrude,
    )
    from scadview.api.surface import (
        mesh_from_heightmap,
        surface,
    )
    from scadview.api.text_builder import (
        SIZE_MULTIPLIER,
        text,
        text_polys,
    )
    from scadview.api.utils import manifold_to_trimesh


# Things to expose at the top level
__all__ = [
    "Color",  # type: ignore[reportUnsupportedDunderAll]
    "set_mesh_color",  # type: ignore[reportUnsupportedDunderAll]
    "ProfileType",  # type: ignore[reportUnsupportedDunderAll]
    "linear_extrude",  # type: ignore[reportUnsupportedDunderAll]
    "mesh_from_heightmap",  # type: ignore[reportUnsupportedDunderAll]
    "surface",  # type: ignore[reportUnsupportedDunderAll]
    "SIZE_MULTIPLIER",  # type: ignore[reportUnsupportedDunderAll]
    "text",  # type: ignore[reportUnsupportedDunderAll]
    "text_polys",  # type: ignore[reportUnsupportedDunderAll]
    "manifold_to_trimesh",  # type: ignore[reportUnsupportedDunderAll]
]

# Map attribute names to (module, attribute) so we can lazy-load
_lazy_map = {
    "Color": ("scadview.api.colors", "Color"),
    "set_mesh_color": ("scadview.api.colors", "set_mesh_color"),
    "ProfileType": ("scadview.api.linear_extrude", "ProfileType"),
    "linear_extrude": ("scadview.api.linear_extrude", "linear_extrude"),
    "mesh_from_heightmap": ("scadview.api.surface", "mesh_from_heightmap"),
    "surface": ("scadview.api.surface", "surface"),
    "SIZE_MULTIPLIER": ("scadview.api.text_builder", "SIZE_MULTIPLIER"),
    "text": ("scadview.api.text_builder", "text"),
    "text_polys": ("scadview.api.text_builder", "text_polys"),
    "manifold_to_trimesh": ("scadview.api.utils", "manifold_to_trimesh"),
}


def __getattr__(name: str):
    """Lazy attribute access for top-level scadview API."""
    try:
        module_name, attr_name = _lazy_map[name]
    except KeyError:
        raise AttributeError(f"module 'scadview' has no attribute {name!r}") from None
    # Import the real module and pull out the attribute
    module = __import__(module_name, fromlist=[attr_name])
    value = getattr(module, attr_name)

    # Cache it in globals so next access is fast
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    # Helps tools that use dir() to discover members
    return sorted(list(globals().keys()) + list(_lazy_map.keys()))


def main():
    from scadview.__main__ import main as main_func

    main_func()
