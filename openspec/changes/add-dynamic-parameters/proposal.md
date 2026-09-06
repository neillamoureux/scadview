## Why

SCADview currently invokes `create_mesh()` without arguments, so users must edit
Python source whenever they want to explore a model dimension or other variable.
Defaulted function parameters already provide a natural model-input contract;
exposing them in the UI would make iterative geometry exploration much faster.

## What Changes

- Detect supported defaulted parameters on the user module's `create_mesh`
  function.
- Display those parameters as controls in the SCADview UI, initialized from
  their Python defaults.
- Regenerate the mesh when a valid control value changes.
- Preserve parameter values across feature toggles and reloads of the same
  module, while resetting them for a different module.
- Validate parameter values and report invalid input without submitting a bad
  load request.
- Correlate load requests and results so rapid parameter changes cannot display
  stale geometry.
- Keep required parameters, arbitrary object defaults, and range-dependent
  slider controls outside the initial scope.

## Capabilities

### New Capabilities

- `create-mesh-parameters`: Discover supported defaulted `create_mesh`
  parameters, expose them as UI controls, and use their values when rebuilding
  the mesh.

### Modified Capabilities

None.

## Impact

- Extends the user-module loading and invocation contract.
- Adds serializable parameter metadata and values to the loader command/result
  protocol.
- Adds controller state and observables for parameter values.
- Adds dynamic parameter controls to the wx UI.
- Requires tests for signature discovery, process-boundary propagation,
  controller persistence, stale-result handling, and UI event routing.
- Does not add a runtime dependency.
