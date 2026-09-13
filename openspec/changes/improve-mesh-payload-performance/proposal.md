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
- Make renderer-facing inputs payload-only and remove `Trimesh` imports,
  reconstruction, and geometry construction from production renderer modules.
- Construct built-in startup, loading, and base-axis geometry outside the renderer
  and inject it as payload-based scene assets.
- Keep the renderer responsible for GL resource lifecycle, scene transforms,
  visibility, drawable construction, and draw ordering.
- Preserve current rendering semantics, including mesh-level color, transparency,
  framing, incremental results, feature-debug lists, and triangle-edge display.
- Retain the final normalized `Trimesh` in the loader process as the lossless
  source of truth and expose it only through an asynchronous export protocol;
  treat `MeshPayload` as a rendering/transport view rather than an export
  representation.
- Add an explicit load-result envelope describing phase, revision, generation,
  payload, and exportability so finality and ownership are not inferred from
  payload shape, sequence numbers, or debug flags.
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

- Affects the internal loader result protocol, controller mesh ownership,
  composition of built-in scene assets, renderer input seam, and export conversion
  path.
- Adds an internal result-state model and final-snapshot ownership boundary;
  these do not expand the public `create_mesh` or renderer APIs.
- Requires focused unit/integration coverage plus manual visual checks for edges,
  transparency, colors, framing, built-in assets, and debug rendering, along
  with export-fidelity and export-lifecycle coverage.
- Does not change public SCADview imports, accepted `create_mesh` return types,
  export availability, or add dependencies.
- Keeps `Trimesh` in the geometry-authoring and normalization domain and in the
  loader-owned export boundary, but removes it from queue payloads, controller,
  UI, and production renderer modules.
