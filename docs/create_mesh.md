# Creating a Mesh

{{ project_name }}'s primary use it to help you iteratively create a mesh.
When you load/reload a Python script into {{ project_name }} as you work on it,
it executes the `create_mesh` function,
and shows the returned mesh.

## create_mesh Signature

The function `create_mesh` must:

- Take no parameters
- Returns a `Trimesh`, `Manifold` or `list[Trimesh | Manifold]` 

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
displaying each object separately.
It is intended to be used for debugging purposes. 
Sometimes, if you are getting unexpected results, 
returning the objects in the `list` 
rather than as a single mesh before you've combined them,
you can see what went wrong.

Note when returning a `list`, 
the "Export" feature is not available.

## Using Color and Transparency

[`set_mesh_color`](/api/#meshsee.set_mesh_color) may be applied to a `Trimesh`, 
which affects its color and transparency.
This allows you to see different meshes in the list in different colors,
and make them transparent so you can see other meshes hidden inside.
`set_mesh_color` only works for `Trimesh` objects, 
and colors do not survive boolean operations.

`set_mesh_color` can alos be useful when returning a single `Trimesh`,
for example if you are removing hidded voids.

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

As with `create_mesh` as a "regular" function, 
you can yield a singular mesh or a list of them.
As above, yielding a list also puts {{ project_name }} into debug mode.




