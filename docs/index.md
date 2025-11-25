# Welcome to  Meshsee

Meshsee enables quickly viewing and iterating on scripted 3d models created by [Trimesh](https://trimesh.org/) or [manifold3d](https://pypi.org/project/manifold3d/).
It has a 3d viewer - you create a 3d (Mesh) that you can view (see) - Meshsee!  
You do this by running Meshsee, writing code to create a Trimesh object, 
and loading it from the Meshsee UI.

## How it works

Meshsee enables a iterative work flow to build Trimesh objects.

1.  Run Meshsee
1.  Create a new python file, and 
1.  Write a `create_mesh` function code to build a Trimesh object.  
1.  Load the Python file into Meshsee.
1.  Meshsee shows you the mesh.  You can move the camera around to inspect your mesh.
1.  Edit your Python file to modify your mesh.
1.  Reload and view the modified mesh.
1.  Repeat the edits and reloads.

## Getting Started

### Installation

If you have python 3.11 or greater, you can install Meshsee directly into your
system.  Or, as is always a good practice, set up a python virtual environment and activate it - see [Creating virual environments](https://docs.python.org/3/library/venv.html#creating-virtual-environments).

Meshsee requires python 3.11 or greater, 
so install an appropriate version in your virtual environment
(or system if running without the virtual environment).

First install Trimesh so you can script your 3d models (activate your virtual environment first):

`pip install trimesh`

Trimesh has optional modules you can add.  
Read its docs to determine which ones will help you most.

To install, Meshsee run 

`pip install meshsee`

If you already have a project using Trimesh set up, add meshsee to that project instead and install there.

### Running

To run: `python -m meshsee`

The first time you run, it may take longer than when you run it in future runs.

### Loading in your model

Create a file with the following python code:

```python
from trimesh.creation import icosphere


def create_mesh():
    return icosphere(radius=40, subdivisions=3)
```

Notice you don't need to import the meshsee package.

Use the Load button on the Meshsee UI to load the file.

You should see a sphere!

### Modify and reload

Now change the subdivisions parameter in your code to 2:

```python
from trimesh.creation import icosphere


def create_mesh():
    return icosphere(radius=40, subdivisions=2)
```

Click Reload. You should see an updated sphere with fewer triangles.


