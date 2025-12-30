# Creating a Golf Ball

You have a golf date, 
but have misplaced all of your golf balls.
You decide to 3D print some.

## Step 1: Set up

Follow the instructions in [Getting Started](index.md#getting-started)

## Step 2: Create a ball

1. First step is to create a ball.
- Create a python file, and call it `golf_ball.py`
1. Using [Trimesh](https://trimesh.org){target="_blank"} to create a ball is your first step, 
so you look at the creation api and see [icosphere](https://trimesh.org/trimesh.creation.html#trimesh.creation.icosphere){target="_blank"} which seems appropriate.
1.  Edit `golf_ball.py` and write:
```python
from trimesh.creation import icosphere

def create_mesh():
    return icosphere()
```
1.  Let's see what it looks like. 
If you haven't already run from the command line:
```bash
python -m {{ package_name }}
```
Or you may need to run:
```bash
python3 -m {{ package_name }}
```
The {{ project_name }} UI should appear.
1.  Click the "Load py..." button.
    - This opens a file dialog.
    Choose the file you've just created, 
    `golf_ball.py`.
    - This should load the file
    and show you a sphere.
    - If you don't see a sphere,
    check the output in the command line for any error messages
    and edit `golf_ball.py` to fix them.
    - Click thhe "Reload" button to reload the file; 
    if all errors are corrected,
    you should see the sphere.

## Step 3: Experiment with `icosphere`
Let's take a look at what options `icosphere` has to offer.
The api docs show 3 parameters:
- `subdivisions`
- `radius`
- `kwargs`

### Subdivisions
Our plan is to put one dimple in each subdivision, 
so let's see what 1 subdivision looks like.
- Change the code to set `subdivisions=1` and hit "Reload":
```python
from trimesh.creation import icosphere

def create_mesh():
    return icosphere(subdivisions=1)
```
Hmmm... looks like it could be smoother.
Let's get some information about the ball.
`icosphere` is a [Trimesh](https://trimesh.org/trimesh.base.html),
which has a wealth of attributes and methods you can use on meshes you create.
Let's add a print statement to show the number of vertices and faces:
```python
from trimesh.creation import icosphere

def create_mesh():
    ball = icosphere(subdivisions=1)
    print(f"Created ball with {len(ball.vertices)} vertices and {len(ball.faces)} faces")
    return ball
```
Note that we have now created variable, `ball`,
so we can get some information about it
before we return it as the output of the `create_mesh` function.

- Hit "Reload" and check the output in the command line:
```cli
Created ball with 42 vertices and 80 faces
```

80 faces means 80 dimples with our 1-dimple-per-face-plan.
We read the Wikipedia article and discover:

- There is no limit to the number of dimples
- Most golf balls have 300-500 dimples
- The record is 1070 dimples.

So we'd like to be in the 300-500 range,
let's up `sudivisions=2` by editing one line:
```python
    ball = icosphere(subdivisions=2)
```
The hit "Reload".

Great, that looks smoother,
and the command line output is
```cli
Created ball with 162 vertices and 320 faces
```
320 faces!  
We are in the 300 - 500 range already.
If you like, you can also try `subdivisions=3`

### Radius

That Wikipedia article continues to deliver!
It says a golf ball must have a diameter of not less than 42.67 mm.
(We will use metric measurements - 
but {{ project_name }} itself does not assign inches, millimeters, 
or any other size to the units).

Let modify that one line again and hit "Reload":
```python
    ball = icosphere(subdivisions=2, radius=42.67/2)
```
You should now see a larger ball.

## Interlude: Play with the UI.

Let's see what you can do with the {{ project_name }} UI.
We've already used a couple of buttons.  

### Controls
Here is what all of the buttons and other controls do - try them out!

- Load.py...
    - Loads a python file, and runs the `create_mesh` function in it, 
    and displays the returned `Trimesh`
    - The `create_mesh` function must take no parameters,
    and return a `Trimesh`, 
    like a `icosphere` or a `box`, 
    or a `Trimesh` created from other `Trimesh`es using geometric boolean methods,
    such as [union](https://trimesh.org/trimesh.base.html#trimesh.base.Trimesh.union){target="_blank"}
    or [difference](https://trimesh.org/trimesh.base.html#trimesh.base.Trimesh.difference){target="_blank"}.
    - `trimesh` is a rich package with lots of other ways to create `Trimesh`es.
- Reload
    - Reload the last file you've loaded, run it, and display the result.
    - This enables quick iterations on viewing your changes in the UI
- Export
    - Export the mesh to a file suitable for 3D printing, like `obj` or `stl`,
    or some other 3D software.
    The available 
    - You may see errors that tell you a package is missing.
    You can either export using a different format, or install the misssing package.
    For example, when exporting in the `dae` format, you might see:
    ```
    ERROR meshsee.ui.wx.main_frame: Failure on export: missing `pip install pycollada`
    ```
    which means you need to install the `pycollada` package.
    And when exporting the `3mf` format, 
    ```
    ERROR meshsee.ui.wx.main_frame: Failure on export: No module named 'networkx'
    ```
    means you need to install the `networkx` package.
- Frame
    - Point the camera to the centre of your mesh, 
    and move it forward or backwards so it fills a large part of the screen.
    - This is useful if you've used the mouse and keyboard controls 
    and want to see the entire mesh at a reasonable distance.
- XYZ
    - Move to [1, -1, 1] and frame.
    This gives a nice canonical view, with:
        - +X pointing right and towards the screen
        - +Y pointing right and away from the screen
        - +Z pointing up
- X
    - Move to [1, 0, 0] and frame.
    - This shows the mesh from the +X side
- Y
    - Move to [0, 1, 0] and frame.
    - This shows the mesh from the +Y side
- Z
    - Move to [0, 0, 1] and frame.
    - This shows the mesh from (you guessed it!) the +Z side
- Grid
    - When activated, 
    this projects a grid on the mesh.
    Each grid line is the intersection of a plane perpendicular to the X, Y and Z axes
    with the mesh.
    - There is a grid line every 0.1 unit, with larger lines at 1 and 10.
    - You can use this to visually check sizes of fine details.
- Perspective/Orthogonal
   - These change the camera from showing a perspective view,
   where parallel line intersect at the "infinity" (horizon),
   or an orthogonal view, where parallel lines in 3D are shown parallel in 2D.
   - A perspective view simulate human vision, and shows further away objects as smaller.
   - An orthogonal view show objects of the same size in 3D as the same size in 2D, 
   but can confuse understanding placement.
- Axes
    - Turns off and on the display of the X, Y, and Z axes.
- Edges
    - Shows all of the face edges in the mesh.
- Gnomon
    - Show the gnomon - 3 half-axes in the bottom left, 
    that shows oriention of the scene with respect to the camera.

### Mouse and keyboard

The mouse (or trackpad) and keyboard move the camera 
so you can view your mesh from different angles.

- Arrow keys
    - Move left (or key A), right (D), forward (W) or back (S)
- Letter keys only
    - Move up (E) or down (Q)
- Mouse drag
    - Orbit the mesh
- Mouse scroll
    - Move forward or back

These controls enable you to load 
and quickly reload your Python script 
to view your mesh.
You can view from different angles
and distances,
and use the different camera projections
and grid to inspect your mesh closely.

## Step 4: Add dimples

Now we want to add dimples.
We will add a dimple at the center of each face,
sizing them somewhat smaller than the face.

Let's start by adding one dimple.  
We don't know the right size yet, 
so let's start with 1 mm diameter

We create a `icosphere` of 1 mm diameter,
and "subtract" (remove it) from the ball.

We add a line to create a dimple,
and return `ball.subtract(dimple)`

Notice that we `apply_translation` 
to move the dimple to the edge of the ball.

```python
from trimesh.creation import icosphere

def create_mesh():
    ball = icosphere(subdivisions=2, radius=42.67/2)  
    print(f"Created ball with {len(ball.vertices)} vertices and {len(ball.faces)} faces")
    dimple = icosphere(subdivisions=2, radius=1/2).apply_translation([0, 0, 42.67])
    return ball.subtract(dimple)
```

When hitting "Reload", something bad happens - 
no ball, and the screen turns red.
Something when wrong.  

The screen turning red indicates a problem with your code.
Check the command line output. 
In this case we see:

```
[MainProcess 44881] ERROR meshsee.ui.wx.main_frame: 'Trimesh' object has no attribute 'subtract'
```

Oh - right, my fault, 
we used the incorrect name for "subtracting" a mesh from another.
The correct name is `difference`, so let change the `return` line to:
```python
    return ball.difference(dimple)
```
and hit "Reload".

Great!  Now the ball is showing again, 
the background is green (which is good).

But no dimple. 
You can move the camera all around 
but the dimple does not show anywhere.
Something else is wrong.
You probably saw it in the script,
but let's suppose you don't know what is wrong.

## Step 5 Debug

{{ project_name }} enables debugging by:

- Enabling viewing multiple meshes at the same time
- Setting colors and transparency of the meshes.

So let's try this out.

To enable seeing multiple meshes, 
return them in an array.

So let's:

- Make the dimple bigger so that it is easier to see (say `radius=10`)
- Comment out our `return` line and instead have:
```python
    dimple = icosphere(subdivisions=2, radius=10).apply_translation([0, 42.67, 0])
    # return ball.difference(dimple)
    return [ball, dimple]
```
- Press "Reload" and we see two balls - 
the smaller one a distance away from the main ball.
- Of course - we moved it the full diameter instead of the radius.
- We need to halve the diameter - that is 11.335.
```python
    dimple = icosphere(subdivisions=2, radius=10).apply_translation([0, 11.335, 0])
```
- Press "Reload".
- Now the large dimple has completely disappeared! What!

Again, you probably saw how I messed up, but let's debug anyway.
Once a mesh is complete, 
and you don't intend to perform any more operations on it,
you can assign it a color and an opaqueness (alpha).

- Colors are a list or typle of 3 floats from 0.0 - 1.0,
representing the red, green and blue values.
- `alpha` is a value betweeh 0.0 and 1.0 as well.
    - 0.0 is completely transparent
    - 1.0 is completely opaque

So let's:

-  Make the `ball` red (`color=[1, 0, 0]`)
and semi-transparent (`alpha=0.5`)
- Make the `dimple` blue (`color=[0, 0, 1]`)
with the same alpha.
- To set the color, we import `set_mesh_color` from {{ package_name }}
```python
from {{ package_name }} import set_mesh_color
```
```python
    set_mesh_color(ball, [1.0, 0, 0], alpha=0.5)
    set_mesh_color(dimple, [0, 0, 1.0], alpha=0.5)
```
- Put this all together:
```python
from trimesh.creation import icosphere
from meshsee import set_mesh_color

def create_mesh():
    ball = icosphere(subdivisions=2, radius=42.67/2)  
    print(f"Created ball with {len(ball.vertices)} vertices and {len(ball.faces)} faces")
    dimple = icosphere(subdivisions=2, radius=10).apply_translation([0, 11.335, 0])
    set_mesh_color(ball, [1.0, 0, 0], alpha=0.5)
    set_mesh_color(dimple, [0, 0, 1.0], alpha=0.5)
    # return ball.difference(dimple)
    return [ball, dimple]
```

Now we can see that our dimple is inside the main ball.
I shouldn't have done the math in my head!

Let's clean up the script a bit by giving names to some of our values.
This makes the script easier to read, 
and easier to modify.
We will add before `create_mesh` some "constants":
```python
...
GOLF_BALL_RADIUS = 42.67 / 2
DIMPLE_RADIUS = 10
SUBDIVISIONS = 2

def create_mesh():
    ...
```
Replacing the values in the script, we get:
```python
from trimesh.creation import icosphere
from meshsee import set_mesh_color

GOLF_BALL_RADIUS = 42.67 / 2
DIMPLE_RADIUS = 10
SUBDIVISIONS = 2

def create_mesh():
    ball = icosphere(subdivisions=SUBDIVISIONS, radius=GOLF_BALL_RADIUS)  
    print(f"Created ball with {len(ball.vertices)} vertices and {len(ball.faces)} faces")
    dimple = icosphere(subdivisions=SUBDIVISIONS, radius=DIMPLE_RADIUS).apply_translation([0, GOLF_BALL_RADIUS, 0])
    set_mesh_color(ball, [1, 0, 0], alpha=0.5)
    set_mesh_color(dimple, [0, 0, 1], alpha=0.5)
    # return ball.difference(dimple)
    return [ball, dimple]

```
- Press "Reload" to make sure this works (it should).

## Step 6: Make all the dimples

Now it is time to make all of the dimples.
- Make one for each face.
- Translate (move) it to the center of the face.

`Trimesh`es store vertices and faces as [numpy ndarrays](https://numpy.org/doc/stable/reference/generated/numpy.ndarray.html).  
`numpy` is a very fast package for preforming calculations on large arrays.
We will take advantage of some of this,
but it can get confusing if we go too deep.
So we will just scratch the surface of what `numpy` can do.

Our strategy:
- Iterate through each face
```python
    for face in ball.faces:
```
- Get the vertices for each face.
```python
        verts = ball.vertices[face]
```
- Find the center of each face. We use the numpy `mean` function.
```python
        face_center = verts.mean(axis=0)
```
- Find the distance from the first vertex in the face to the center.
We use the numpy `norm` function:
```python
        dist_to_center = np.linalg.norm(verts[0] - face_center)
```
- Make a dimple some fraction of this (say 1/6), and place at the center.
```python
        dimple_r = dist_to_center / 6.0
        dimple_mesh = icosphere(subdivisions=2, radius=dimple_r, center=face_center)
        dimple_mesh.apply_translation(face_center)
```
- Put this all together, plus:
    - Replacing `DIMPLE_RADIUS` with `DIMPLE_RADIUS_FRACTION`
    - Keeping the dimples in an array
```python
import numpy as np
from meshsee import set_mesh_color
from trimesh.creation import icosphere


GOLF_BALL_RADIUS = 42.67 / 2
DIMPLE_RADIUS_FRACTION = 1 / 6
SUBDIVISIONS = 2


def create_mesh():
    ball = icosphere(subdivisions=SUBDIVISIONS, radius=GOLF_BALL_RADIUS)
    print(
        f"Created ball with {len(ball.vertices)} vertices and {len(ball.faces)} faces"
    )
    set_mesh_color(ball, [1, 0, 0], alpha=0.5)
    meshes = [ball]
    dimples = []
    for face in ball.faces:
        verts = ball.vertices[face]
        face_center = verts.mean(axis=0)
        dist_to_center = np.linalg.norm(verts[0] - face_center)
        dimple_r = dist_to_center * DIMPLE_RADIUS_FRACTION
        dimple_mesh = icosphere(
            subdivisions=SUBDIVISIONS, radius=dimple_r, center=face_center
        )
        dimple_mesh.apply_translation(face_center)
        dimples.append(dimple_mesh)
    return [ball] + dimples
```

This shows a transparent ball with a lot of small balls distributed around its surface.
Not quite a golf ball, 
but it shows where the dimples will be
and their size.  
It looks good, but I want them bigger,
so we set
```python
DIMPLE_RADIUS_FRACTION = 1 / 4
```

## Step 7: Carve out the dimples

Now all that remains is:
- Carve out each dimple (`difference`)
- Return a final mesh (not an array) so that "Export" is available.

Let's carve out each dimple:
```python
```








