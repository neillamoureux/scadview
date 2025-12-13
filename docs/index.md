# Welcome to  {{ project_name }}

Meshsee enables quickly viewing and iterating on scripted 3d models created by [Trimesh](https://trimesh.org/) or [manifold3d](https://pypi.org/project/manifold3d/).
It has a 3d viewer - you create a 3d (Mesh) that you can view (see) - Meshsee!  
You do this by running Meshsee, writing code to create a Trimesh object, 
and loading it from the Meshsee UI.

## How it works

Meshsee enables a iterative work flow to build Trimesh objects.

1.  Create a new python file, and 
1.  Write a `create_mesh` function code to build a Trimesh object.  
1.  Run Meshsee
1.  Load the Python file into Meshsee.
1.  Meshsee shows you the mesh.  You can move the camera around to inspect your mesh.
1.  Edit your Python file to modify your mesh.
1.  Reload and view the modified mesh.
1.  Repeat the edits and reloads.

## Getting Started

### Installation

Check that you have Python 3.11 or greater via

`python --version`

or, if the `python` command cannot be found:

`python3 --version`

If Python 3.11 or greater is installed on your system, 
you can install Meshsee directly into your system.

#### Virtual venv option

As is always a good practice, 
set up a Python virtual environment and activate it: 
- see [Creating virtual environments](https://docs.python.org/3/library/venv.html#creating-virtual-environments).

#### Install Trimesh

First install Trimesh so you can script your 3d models 
(if using a virtual environment, activate it first):

`pip install trimesh`

Trimesh has optional modules you can add.  
Read its docs to determine which ones will help you most.

#### Install Meshsee

To install, Meshsee run 

`pip install git+https://github.com/neillamoureux/meshsee.git@main`

If you already have a project using Trimesh set up, add meshsee to that project instead and install there.

### Running

To run: `python -m meshsee`

The first time you run, 
it can take some time to set up the user interface,
and so it may take longer than when you run it in future runs.

Notice that your console/terminal shows output from the Meshsee module.

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

### Export

Once you are happy with your mesh, 
you can export it for 3d printing
or for loading other 3d software.

1. Click the `Export` button.
1. Choose a format. 


