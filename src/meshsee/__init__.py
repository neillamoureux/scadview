# Importing the modules takes time the first run, so we use lazy loading
# to speed up the initial import of meshsee.

# Things to expose at the top level
# type: ignore[reportUnsupportedDunderAll]
__all__ = [
    "Color",
    "set_mesh_color",
    "ProfileType",
    "linear_extrude",
    "mesh_from_heightmap",
    "surface",
    "text",
    "text_polys",
    "manifold_to_trimesh",
]

# Map attribute names to (module, attribute) so we can lazy-load
_lazy_map = {
    "Color": ("meshsee.api.colors", "Color"),
    "set_mesh_color": ("meshsee.api.colors", "set_mesh_color"),
    "ProfileType": ("meshsee.api.linear_extrude", "ProfileType"),
    "linear_extrude": ("meshsee.api.linear_extrude", "linear_extrude"),
    "mesh_from_heightmap": ("meshsee.api.surface", "mesh_from_heightmap"),
    "surface": ("meshsee.api.surface", "surface"),
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
