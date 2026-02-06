# SCADview
An application to view 3D meshes created from Python.

## Python versions supported

SCADview supports Python versions 3.11 - 3.13,
since some packages it depends on do not supply wheels for versions > 3.13.
Attempting to install in 3.14 or higher may result in an error.

## How it works

SCADview enables a iterative work flow to build Trimesh objects.

1.  Create a new python file, and 
1.  Write a `create_mesh` function code to build a Trimesh object.  
1.  Run SCADview on the command line via: `scadview`
1.  Load the Python file into SCADview.
1.  SCADview shows you the mesh.  You can move the camera around to inspect your mesh.
1.  Edit your Python file to modify your mesh.
1.  Reload and view the modified mesh.
1.  Repeat the edits and reloads.

## Getting Started

### Installation

Open your terminal application
for example `cmd` in Windows
or `Terminal.app` under Applications > Utilties > Terminal.app in macOS.

In the terminal, check that you have Python 3.11 through 3.13 or greater via

`python --version`

or, if the `python` command cannot be found:

`python3 --version`

If Python 3.11 through 3.13 is installed on your system, 
you can install SCADview directly into your system.

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

#### Install SCADview

To install, SCADview run 

`pip install scadview`

If you already have a project using Trimesh set up, install scadview into that project instead and install there.

### Running

To run: `scadview`

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

![Splash](./docs/images/splash_window.png){ .md-image width=400 }

Once it has initialized, you should see the main user interface:
![Startup Window](./docs/images/startup_window.png){ .md-image width=700 }

Notice that your terminal shows output from the scadview module.

### Loading in your model

Using a code editor,
create a file with the following python code:

```python
from trimesh.creation import icosphere


def create_mesh():
    return icosphere(radius=40, subdivisions=3)
```

Notice that you don't need to import the scadview package.

Save the file:

- If you did not create a virtual environment,
you can save it anywhere on your system.
- If you installed in a virtual environment,
save your file in that folder.

Use the Load button on the SCADview UI to load the file.

You should see a sphere!
![sphere](./docs/images/getting_started_ball.png)

### Modify and reload

Now change the subdivisions parameter in your code to 2:

```python
from trimesh.creation import icosphere


def create_mesh():
    return icosphere(radius=40, subdivisions=2)
```

Click Reload. You should see an updated sphere with fewer triangles.
![sphere_2](./docs/images/getting_started_ball_2.png)

### Export

Once you are happy with your mesh, 
you can export it for 3d printing
or for loading other 3d software.

1. Click the `Export` button.
1. Choose a format. 
1. Click Save.

The Export dialog may look different on your computer.
![export](./docs/images/getting_started_export.png)




## Versioning
SCADview follows [Semantic Versioning 2.0.0](https://semver.org/).  
In short: MAJOR versions for incompatible API changes, MINOR for backward-compatible
features, and PATCH for backward-compatible bug fixes. While the major version
is 0, we may introduce breaking changes in minor releases.

---

## 📜 License

SCADview is open-source software licensed under the [Apache License, Version 2.0](LICENSE).

You are free to use, modify, and redistribute this software — including in commercial
applications — provided you include the license text above and retain copyright notices.

---

## ⚠️ Disclaimer

SCADview is provided **“as is”**, without warranty of any kind.
It is intended for visualization, analysis, and experimentation purposes.
It is **not designed for safety-critical, medical, or certified manufacturing applications**.
Use at your own discretion.

---

## 🏷️ Name and Branding

The name **SCADview** and its associated logo are trademarks of **Neil Lamoureux**.  
While you are free to fork and modify the code under the Apache License,  
you **may not use the name SCADview** to promote or distribute modified versions  
without prior written permission.  
Please choose a distinct name for derivative works (e.g. *“YourTool, based on SCADview*).
