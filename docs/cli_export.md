# Command-Line Export

This page shows how to run a `create_mesh` script from the command line so you
can pass parameters, build the mesh, and export it with Trimesh. This is useful
for batch runs and for stepping through mesh creation in a debugger.

## Pattern: keep `create_mesh` UI-friendly

To keep the {{ project_name }} UI working, make sure `create_mesh` takes no required
parameters. You can still accept CLI arguments by adding a separate `main()`.

```python
{% include "../examples/cli_export.py" %}
```

Run it from the command line:

```bash
python path/to/your_script.py --radius 12 --height 30 --out ./build/cyl.stl
```

## Using Manifold or generators

- If `create_mesh` returns a `Manifold`, convert it before exporting:

```python
from {{ package_name }} import manifold_to_trimesh

mesh = manifold_to_trimesh(create_mesh(...))
mesh.export(args.out)
```

- If `create_mesh` yields intermediate meshes, export only the final one:

```python
latest = None
for step in create_mesh(...):
    latest = step
if latest is not None:
    latest.export(args.out)
```

## Debugging from the command line

Running from the CLI makes it easy to step through `create_mesh` with a
standard debugger:

```bash
python -m pdb path/to/your_script.py --radius 12 --height 30 --out ./build/cyl.stl
```

This lets you inspect variables, pause between boolean operations, and verify
dimensions without launching the UI.

## Debugging in VS Code

If you prefer VS Code, create or update `.vscode/launch.json` with a launch
profile that passes the same args:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Run create_mesh script",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/path/to/your_script.py",
            "args": [
                "--radius",
                "12",
                "--height",
                "30",
                "--out",
                "${workspaceFolder}/build/cyl.stl"
            ],
            "console": "integratedTerminal"
        }
    ]
}
```

Set a breakpoint inside `create_mesh`, then run the configuration from the
Run and Debug panel to step through the mesh creation.
