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

### Mouse and Keyboard

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
