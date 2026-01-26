# Examples

This page explains each script in `examples/` and lets you expand the full source.

## cli_export.py

Command-line example that parses arguments, builds a mesh, and exports it with Trimesh.

<details>
<summary>Source</summary>


```python

{% include "../examples/cli_export.py" %}

```
</details>
![CLI Export](images/cli_export.png)

## colors.py

Builds a list of colored text meshes, one per `Color` enum value. This shows how returning a `list[Trimesh]` enables debug-mode display of multiple meshes at once.

<details>
<summary>Source</summary>

```python

{% include "../examples/colors.py" %}

```
</details>
![Colors](images/colors.png)

## cube_minus_sphere.py

Creates boxes and spheres with translucent colors and returns a list of intermediate shapes. It demonstrates boolean experimentation (difference is commented) and using colors to inspect overlaps.

<details>
<summary>Source</summary>

```python

{% include "../examples/cube_minus_sphere.py" %}

```
</details>
![Cube Minus Sphere](images/cube_minus_sphere.png)

## invalid_code.py

Imports a non-existent module to force an import error. Useful for verifying error handling.

<details>
<summary>Source</summary>

```python

{% include "../examples/invalid_code.py" %}

```
</details>
![Invalid Code](images/red.png)

## invalid_code_2.py

Calls an undefined function (`prin`) to trigger a runtime error. Useful for testing error reporting in the UI.

<details>
<summary>Source</summary>

```python

{% include "../examples/invalid_code_2.py" %}

```
</details>
![Invalid Code 2](images/red.png)

## koch_snowflake_vase.py

Generates a Koch-snowflake outline, then uses `linear_extrude` with twist, slices, and scale to create a tall, twisted vase. Demonstrates procedural 2D shape refinement and extrusion.

<details>
<summary>Source</summary>

```python

{% include "../examples/koch_snowflake_vase.py" %}

```
</details>
![Koch Snowflake Vase](images/koch_snowflake_vase.png)
## lego.py

Procedurally builds a Lego-style brick with pegs and under-cylinders, yielding intermediate steps as it unions geometry. Demonstrates a complex parametric build with incremental yields.

<details>
<summary>Source</summary>

```python

{% include "../examples/lego.py" %}

```
</details>
![Lego](images/lego.png)
## messner_mani.py

Uses `manifold3d` to carve a cube into a Menger-sponge-like structure by repeatedly subtracting smaller cubes. Yields intermediate meshes as a list to visualize each step in debug mode.

<details>
<summary>Source</summary>

```python

{% include "../examples/messner_mani.py" %}

```
</details>
![Messner Manifold](images/messner_mani.png)
## mobius.py

Sweeps a thin rectangle along a circular path with a half twist to form a Mobius strip. Shows `sweep_polygon` with twist and slice control.

<details>
<summary>Source</summary>

```python

{% include "../examples/mobius.py" %}

```
</details>
![Mobius](images/mobius.png)
## mushroom.py

Builds a mushroom-like shape using icospheres, annuli, and booleans. It sets logging to DEBUG and includes metadata-based coloring notes.

<details>
<summary>Source</summary>

```python

{% include "../examples/mushroom.py" %}

```
</details>
![Mushroom](images/mushroom.png)
## simple_animation.py

A generator that yields a moving box with `sleep(...)` between frames. This is the minimal animation example.

<details>
<summary>Source</summary>

```python

{% include "../examples/simple_animation.py" %}

```
</details>
![Simple Animation](images/simple_animation.png)
## sphere.py

Returns a single icosphere. This is the simplest possible `create_mesh`.

<details>
<summary>Source</summary>

```python

{% include "../examples/sphere.py" %}

```
</details>
![Sphere](images/sphere.png)
## star_linear_extrude.py

Constructs a 2D star polygon with an inner hole and extrudes it with twist and taper. Demonstrates `linear_extrude` parameters like `twist`, `slices`, and `scale`.

<details>
<summary>Source</summary>

```python

{% include "../examples/star_linear_extrude.py" %}

```
</details>
![Star Linear Extrude](images/star_linear_extrude.png)
## surface_bend.py

Loads a heightmap from the splash image using `surface(...)`, then bends its vertices around an arc and rebuilds a `Trimesh`. This example shows post-processing vertex positions and applying transforms.

<details>
<summary>Source</summary>

```python

{% include "../examples/surface_bend.py" %}

```
</details>
![Surface Bend](images/surface_bend.png)
## surface_.py

Loads a heightmap from the splash image using `surface(...)`.

<details>
<summary>Source</summary>

```python

{% include "../examples/surface.py" %}

```
</details>
![Surface](images/surface.png)
## text.py

Uses `text(...)` with a specific font and alignment options, then scales in Z to add thickness. Demonstrates text mesh creation and font selection.

<details>
<summary>Source</summary>

```python

{% include "../examples/text.py" %}

```
</details>
![Text](images/text.png)
## toothbrush_holder.py

A full parametric design that yields intermediate meshes as it builds a multi-tube holder with labeled name plates and a base. It demonstrates incremental `yield` updates, boolean unions/differences, and procedural layout.

<details>
<summary>Source</summary>

```python

{% include "../examples/toothbrush_holder.py" %}

```
</details>
![Toothbrush Holder](images/toothbrush_holder.png)
## xyz.py

A generator that continuously rotates a frame with cut-out X/Y/Z letters and yields tinted meshes. Demonstrates infinite generators, transforms, booleans, and `set_mesh_color`.

<details>
<summary>Source</summary>

```python

{% include "../examples/xyz.py" %}

```
</details>
![xyz](images/xyz.png)
## xyz_cube.py

Builds a cube with extruded X/Y/Z letters on each face and cuts the opposite letters to form a labeled axis cube. Shows text meshes, transformations, and boolean operations.

<details>
<summary>Source</summary>

```python

{% include "../examples/xyz_cube.py" %}

```
</details>
![XYZ Animation](images/xyz_cube.png)
