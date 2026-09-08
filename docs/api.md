# API Reference

## create_mesh parameter contract

SCADview exposes defaulted `bool`, `int`, `float`, and `str` parameters from a
user module's `create_mesh` function in the Parameters section. Supported
parameters may be ordinary named or keyword-only parameters. Required,
positional-only, variadic, and parameters with unsupported default values are
not exposed as controls. See [Creating a Mesh](./create_mesh.md#interactive-parameters)
for the full behavior and examples.

::: scadview.Color
::: scadview.set_mesh_color
::: scadview.feature
::: scadview.feature_default
::: scadview.surface
::: scadview.mesh_from_heightmap
::: scadview.SIZE_MULTIPLIER
::: scadview.text
::: scadview.text_polys
::: scadview.ProfileType
::: scadview.linear_extrude
::: scadview.manifold_to_trimesh
