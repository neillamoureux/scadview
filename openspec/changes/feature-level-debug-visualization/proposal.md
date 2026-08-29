## Why

Named features currently control whether optional geometry participates in the generated model, while SCADview's existing debug mode visualizes separately returned meshes. Users cannot inspect a feature's source geometry, including subtractive tool volumes, without rewriting their script. A separate feature-debug visualization mode provides that inspection while keeping feature inclusion state unchanged.

## What Changes

- Add a global, session-level `Debug features` UI toggle near the feature controls, disabled by default.
- Retain the Debug features choice across reloads and loading different modules for the
  lifetime of the application session.
- Capture each named feature's source mesh when it is registered, preserving feature name and registration order.
- Keep feature enabled/disabled state independent from feature-debug visualization.
- When feature debug is active, visualize the source meshes of enabled features using the existing debug-list rendering behavior.
- Emit the enabled feature-source snapshot captured so far for every yielded mesh
  during progressive module loads.
- Preserve normal final-mesh loading and rendering when feature debug is inactive.
- Show the normal final mesh when debug mode is active but no feature meshes are registered.
- Keep duplicate registrations of a feature name as separate debug meshes.
- Convert supported `Manifold` feature sources to `Trimesh` for rendering.
- Document that debug geometry represents source geometry or tool volumes, not necessarily final model material.
- Extend `examples/features.py` and its rendered documentation with a Debug features
  walkthrough using its subtractive `cable_cutout` tool volume, and explain that
  debug visualization is separate from each feature's enabled state.

## Capabilities

### New Capabilities

- `feature-debug-visualization`: Visualize registered, enabled feature source geometry as a separate diagnostic mode.

### Modified Capabilities

- None.

## Impact

- Updates feature-context capture, loader command/result handling, controller state, and wx UI controls.
- Reuses the existing list-of-meshes debug renderer and does not add a public user-module API.
- Documents the mode alongside feature and debug-mode documentation, including its
  source/tool-volume meaning and non-exportable diagnostic status.
- Updates the existing feature example and its documentation inclusion; no new user
  module API or separate example file is introduced.
- Adds internal load/debug state and test coverage for feature capture, progressive loads, controller reloads, and UI behavior.
- No new dependencies or changes to the `create_mesh` return contract.
