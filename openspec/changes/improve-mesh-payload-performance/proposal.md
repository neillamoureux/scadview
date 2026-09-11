## Why

Large generated meshes currently cross the loader-process boundary as complete
`Trimesh` objects and are then expanded into repeated per-triangle render data.
This can increase serialization, temporary-memory, and first-frame costs, but the
dominant bottleneck must be measured before committing to a higher-risk shader
redesign.

## What Changes

- Add repeatable measurements for loader-to-main transfer size and time, peak
  memory, payload conversion, and first-frame rendering of representative meshes.
- Introduce a compact internal mesh payload containing the indexed geometry and
  renderer metadata needed after module execution.
- Transfer compact payloads through the existing generation-aware result queue and
  consume them without changing the public `create_mesh` return contract.
- Preserve current rendering semantics, including mesh-level color, transparency,
  framing, incremental results, feature-debug lists, and triangle-edge display.
- Preserve GUI export behavior by safely converting the retained payload to an
  exportable `Trimesh` when required.
- Evaluate fully indexed GPU rendering only after the compact-payload stage is
  measured; adopt it only if benchmarks justify the complexity and visual
  validation confirms parity.
- Keep shared-memory transport and geometry-generation optimization out of scope.

## Capabilities

### New Capabilities

- `mesh-payload-transfer`: Compact internal mesh transfer, compatibility,
  measurement, and gating requirements for renderer optimization.

### Modified Capabilities

None.

## Impact

- Affects the internal loader result protocol, controller mesh ownership, renderer
  input seam, and export conversion path.
- Requires focused unit/integration coverage plus manual visual checks for edges,
  transparency, colors, framing, and debug rendering.
- Does not change public SCADview imports, accepted `create_mesh` return types,
  export availability, or add dependencies.
