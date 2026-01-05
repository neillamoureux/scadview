# Importing the modules takes time the first run, so we use lazy loading
# to speed up the initial import of meshsee.

# This is so the the documetation tools can see these symbols
if False:
    from meshsee.api.colors import (
        Color,
        set_mesh_color,
    )
    from meshsee.api.linear_extrude import (
        ProfileType,
        linear_extrude,
    )
    from meshsee.api.surface import (
        mesh_from_heightmap,
        surface,
    )
    from meshsee.api.text_builder import (
        SIZE_MULTIPLIER,
        text,
        text_polys,
    )
    from meshsee.api.utils import manifold_to_trimesh


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
    "Color": ("meshsee.api.colors", "Color"),
    "set_mesh_color": ("meshsee.api.colors", "set_mesh_color"),
    "ProfileType": ("meshsee.api.linear_extrude", "ProfileType"),
    "linear_extrude": ("meshsee.api.linear_extrude", "linear_extrude"),
    "mesh_from_heightmap": ("meshsee.api.surface", "mesh_from_heightmap"),
    "surface": ("meshsee.api.surface", "surface"),
    "SIZE_MULTIPLIER": ("meshsee.api.text_builder", "SIZE_MULTIPLIER"),
    "text": ("meshsee.api.text_builder", "text"),
    "text_polys": ("meshsee.api.text_builder", "text_polys"),
    "manifold_to_trimesh": ("meshsee.api.utils", "manifold_to_trimesh"),
}


def __getattr__(name: str):
    """Lazy attribute access for top-level meshsee API."""
    try:
        module_name, attr_name = _lazy_map[name]
    except KeyError:
        raise AttributeError(f"module 'meshsee' has no attribute {name!r}") from None

    # Import the real module and pull out the attribute
    module = __import__(module_name, fromlist=[attr_name])
    value = getattr(module, attr_name)

    # Cache it in globals so next access is fast
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    # Helps tools that use dir() to discover members
    return sorted(list(globals().keys()) + list(_lazy_map.keys()))
