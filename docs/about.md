# About {{ project_name }}

{{ project_name }} exists to make scripted CAD iteration fast and pleasant in
Python. You write `create_mesh` functions using Trimesh or Manifold3D, then
reload to see results immediately.

It is inspired by the excellent OpenSCAD, but uses a more common language and
(IMHO) a simpler, more flexible programming model than OpenSCAD's functional
style. The goal is the same: quick, repeatable, parametric modeling.

## What's Included

- A fast reload-and-preview UI for Python-based mesh scripts.
- A small API in {{ package_name }} with OpenSCAD-like helpers.
- Support for meshes built with [Trimesh](https://trimesh.org){target="_blank"}
  or [Manifold3D](https://pypi.org/project/manifold3d/){target="_blank"}.

## Why a separate UI

{{ project_name }} does not ship an editor because there are already many great
ones. This project focuses on the iteration loop and visualization.

Trimesh already offers notebooks and a pyglet viewer, but neither matched the
UI or feedback loop needed for rapid scripted CAD. {{ project_name }} was built
to close that gap.

## Why it is different

- Faster preview and reload than OpenSCAD for many workflows.
- No "fudge factor" needed to ensure boolean subtractions punch through.
- Inspect meshes quickly for size, bounding box, and face layout.
- A small API surface in {{ package_name }} that includes OpenSCAD-like
  functions for familiar workflows.
