# Creating a Mesh

{{ project_name }}'s primary use it to help you iteratively create a mesh.
When you load/reload a Python script into {{ project_name }} as you work on it,
it executes the `create_mesh` function,
and shows the returned mesh.

## create_mesh Signature

The function `create_mesh` must:

- Take no parameters, or all parameters must have default values.
- Return a `Trimesh`, `Manifold` or `list[Trimesh | Manifold]` or... [see below](#incremental-builds).

That is, the function should look like this with type hints 
(but type hints are not required):
```python
from manifold3d import Manifold
from trimesh import Trimesh


def create_mesh() -> Trimesh | Manifold | list[Trimesh | Manifold]:
    ...
```

## `Trimesh` vs `Manifold`

You can choose to return either `Trimesh` or `Manifold` types,
or a list containing items of either type.
The list does not need to have just one type.

[Trimesh](https://trimesh.org){target="_blank"} is simpler to use than
[manifold3d](https://pypi.org/project/manifold3d/){target="_blank"}, 
which creates `Manifold` objects.
But `manifold3d` is highly optimized for geometric boolean operations,
and can be much faster than Trimesh.
So if you are combining 100s of meshes, consider trying out `manifold3d`.

## Debug Mode: Return a `list`

Returning a `list` of objects results in {{ project_name }}
displaying each object in the list.
It is intended to be used for debugging purposes. 
Sometimes, if you are getting unexpected results, 
returning the objects in the `list` 
rather than as a single mesh before you've combined them,
you can see what went wrong.

Note when returning a `list`, 
the "Export" feature is not available.

## Using Color and Transparency

[`set_mesh_color`](api.md#{{ package_name }}.set_mesh_color) may be applied to a `Trimesh`, 
which affects its color and transparency.
This allows you to see different meshes in the list in different colors,
and make them transparent so you can see other meshes hidden inside.
`set_mesh_color` only works for `Trimesh` objects, 
and colors do not survive boolean operations.

`set_mesh_color` can also be useful when returning a single `Trimesh`,
for example if you are removing hidded voids.

## Output and Logging

Console output goes to the terminal where you launched `python -m {{ package_name }}`.
You can use `print(...)` or Python's `logging` module inside your script. If you
need more detail, you can set the logging level in your script.

## Incremental Builds

Displaying intermediate builds of your mesh
as you build it can be useful to see problems 
before a long build completes. 
It also give you a sense of how long the build might take.

{{ project_name }} supports incremental builds.  To do this, 
`create_mesh` can be defined as a `Generator`,
with the signature:
```python
def create_mesh() ->  Generator[[Trimesh | Manifold | list[Trimesh | Manifold]]:
    yield ...
```
For example:
```python
def create_mesh():
    ..create mesh1
    yield mesh1
    ...create mesh2
    yield mesh2
```

As this adds additional renders, 
building incrementatlly is generally slower than a single build.
If you yield very quickly (many times per second),
some renders may be skipped to keep the speed up.

As with `create_mesh` as a "regular" function, 
you can yield a singular mesh or a list of them.
As above, yielding a list also puts {{ project_name }} into debug mode.


## Animation

By pausing between each yield, 
you can animate at a consistent frame rate.

For example:
```python
from time import sleep

from trimesh.creation import box


def create_mesh():
    b = box([10, 10, 20])
    for _ in range(100):
        yield b
        sleep(0.1)
        b.apply_translation([0.2, 0, 0])
```
