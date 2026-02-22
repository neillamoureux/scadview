# SCADview Architecture

SCADview follows a layered, event-driven desktop architecture with explicit process boundaries.

## 1. Single composition root

- Application wiring happens in `src/scadview/__main__.py` and `src/scadview/app.py`.
- Construction order is: renderer factory and adapter, then controller, then UI.

## 2. Dependency direction is inward

- UI code (`src/scadview/ui/wx/*`) depends on `Controller` and `GlWidgetAdapter`.
- `Controller` (`src/scadview/controller.py`) coordinates loading, export, and app state.
- Background loading (`src/scadview/mesh_loader_process.py`) depends on module execution (`src/scadview/module_loader.py`), not on UI.
- Rendering (`src/scadview/render/*`) is isolated from wx widgets via `src/scadview/render/gl_widget_adapter.py`.

## 3. Background work is process-isolated

- Mesh generation runs in a separate process (`MeshLoaderProcess`) and worker thread.
- Main process and loader process communicate only through typed command/result queues (`MpCommandQueue`, `MpLoadQueue`).

## 4. State changes flow through observables

- Cross-component notifications use `Observable` (`src/scadview/observable.py`), not direct callback coupling.
- Load lifecycle is represented by `LoadStatus` (`src/scadview/load_status.py`) and propagated to UI/render.

## 5. User module contract is strict

- Dynamically loaded modules must expose `create_mesh`.
- Allowed return types are `Trimesh`, `Manifold`, or lists of those; values are normalized before render (`src/scadview/mesh_loader_process.py`, `src/scadview/module_loader.py`).

## 6. Rendering is a pure service boundary

- Renderer owns GL context, shaders, camera, and drawables (`src/scadview/render/renderer.py`).
- UI triggers actions (orbit, frame, toggles) through adapter methods, not direct GL calls.

## 7. Operational concerns are centralized

- Multiprocess logging is configured through queue-based logging (`src/scadview/logging_main.py`).
- Local docs and release-doc tasks are centralized in a single script with subcommands (`scripts/docs_tasks.py`).
