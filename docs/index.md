# Welcome to  {{ project_name }}

{{ project_name }} enables quickly viewing and iterating on scripted 3d models created by [Trimesh](https://trimesh.org/) or [manifold3d](https://pypi.org/project/manifold3d/).
SCAD is "scripted computer assisted design", 
and SCADview allows you to view your SCAD models.
You do this by running {{ project_name }}, writing code to create a Trimesh object, 
and loading it from the {{ project_name }} UI.

## Python versions supported

{{ project_name }} supports Python versions 3.11 - 3.13,
since some packages it depends on do not supply wheels for versions > 3.13.
Attempting to install in 3.14 or higher may result in an error.

## How it works

{{ project_name }} enables a iterative work flow to build Trimesh objects.

1.  Create a new python file, and 
1.  Write a `create_mesh` function code to build a Trimesh object.  
1.  Run {{ project_name }} on the command line via: `{{ package_name }}`
1.  Load the Python file into {{ project_name }}.
1.  {{ project_name }} shows you the mesh.  You can move the camera around to inspect your mesh.
1.  Edit your Python file to modify your mesh.
1.  Reload and view the modified mesh.
1.  Repeat the edits and reloads.

## Getting Started

### Installation

Open your terminal application
for example `cmd` in Windows
or `Terminal.app` under Applications > Utilties > Terminal.app in macOS.

In the terminal, check that you have Python 3.11 through 3.13 via

`python --version`

or, if the `python` command cannot be found:

`python3 --version`

If Python 3.11 through 3.13 is installed on your system, 
you can install {{ project_name }} directly into your system.

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

#### Install {{ project_name }}

To install, {{ project_name }} run 

`pip install {{ package_name }}`

If you already have a project using Trimesh set up, install {{ package_name }} into that project instead and install there.

### Running

To run: `{{ package_name }}`

The first time you run, 
it can take some time to set up the user interface,
and so it may take longer than when you run it in future runs.

A splash screen may show on startup.  
If it is not available,
you will see a message in the terminal output:
```
WARNING scadview.ui.splash_window: The splash screen is not available so it will not be shown.
```
Otherwise, you will see:

![Splash](./images/splash_window.png){ .md-image width=400 }

Once it has initialized, you should see the main user interface:
![Startup Window](./images/startup_window.png){ .md-image width=700 }

Notice that your terminal shows output from the {{ package_name }} module.

### Loading in your model

Using a code editor,
create a file with the following python code:

```python
from trimesh.creation import icosphere


def create_mesh():
    return icosphere(radius=40, subdivisions=3)
```

Notice that you don't need to import the {{ package_name }} package.

Save the file:

- If you did not create a virtual environment,
you can save it anywhere on your system.
- If you installed in a virtual environment,
save your file in that folder.

Use the Load button on the {{ project_name }} UI to load the file.

You should see a sphere!
![sphere](images/getting_started_ball.png)

### Modify and reload

Now change the subdivisions parameter in your code to 2:

```python
from trimesh.creation import icosphere


def create_mesh():
    return icosphere(radius=40, subdivisions=2)
```

Click Reload. You should see an updated sphere with fewer triangles.
![sphere_2](images/getting_started_ball_2.png)

### Export

Once you are happy with your mesh, 
you can export it for 3d printing
or for loading other 3d software.

1. Click the `Export` button.
1. Choose a format. 
1. Click Save.

The Export dialog may look different on your computer.
![export](images/getting_started_export.png)


