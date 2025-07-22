# Welcome to  Meshee

Meshee is a enables quickly viewing and iterating on scripted 3d models created by [Trimesh](https://trimesh.org/).
It has a 3d viewer - you create a 3d (Mesh) that you can view (see) - Meshsee!  
You do this by running meshee, writing code to create a Trimesh object, 
and loading it from the Meshsee UI.

## How it works

Meshsee enables a iterative work flow to build Trimesh objects.

1.  Run Meshee
1.  Create a new python file, and 

You write code to build a Trimesh object.  

## Getting Started

### Installation

As is always a good practice, set up a python virtual environment and activate it - see [Creating virual environments](https://docs.python.org/3/library/venv.html#creating-virtual-environments).

Meshee requires python 3.11 or greater, 
so install an appropriate version in your virtual environment.

First install Trimesh so you can script your 3d models:

`pip install trimesh`

Trimesh has optional modules you can add.  
Read its docs to determine which ones will help you most.

To install, Meshee run 

`pip install meshee`

If you already have a project using Trimesh set up, add meshee to that project instead and install there.

### Running

To run: `python -m meshee`

The first time you run, it may take longer than when you run it in future runs.

### Loading in your model

Create a file with the following python code:

```python
from trimesh.creation import icosphere


def create_mesh():
    return icosphere(radius=40, subdivisions=3)
```

Notice you don't need to import the meshee package.

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


