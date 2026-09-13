## Purpose

Define measurable, compatibility-preserving behavior for transferring generated
mesh geometry from the loader process to rendering and export consumers.

## ADDED Requirements

### Requirement: Performance changes are measured against a baseline
The change SHALL provide a repeatable comparison of the existing mesh path and
the compact-payload path using the same representative meshes and environment.
The comparison SHALL report serialized size, conversion and transfer time, peak
memory where supported, and time until the first rendered frame.

#### Scenario: Baseline is captured before transport changes
- **WHEN** implementation begins on the mesh transfer path
- **THEN** the existing path is measured and its environment and mesh sizes are recorded before production behavior is changed

#### Scenario: Compact path is compared fairly
- **WHEN** the compact-payload stage is complete
- **THEN** the same measurements are repeated with the same inputs and environment and the before-and-after results are recorded

### Requirement: Loader results use compact mesh data
The system SHALL represent each successfully normalized mesh crossing the loader
process boundary using contiguous indexed geometry, fixed-width numeric types,
one optional mesh-level color, and only the additional summary data required for
rendering. A successful display result SHALL NOT contain a complete `Trimesh`
object. The loader process SHALL retain the final normalized source separately
when lossless export is available.

#### Scenario: Single mesh result is transferred
- **WHEN** a user module produces one valid mesh
- **THEN** the loader result contains one compact payload with equivalent vertices, triangle faces, shading data, color, bounds, and scale

#### Scenario: Mesh list result is transferred
- **WHEN** a user module produces a valid list or feature-debug output
- **THEN** the loader result preserves mesh order and one independently colored compact payload per non-empty mesh

#### Scenario: Incremental result is transferred
- **WHEN** a generator yields successive valid meshes
- **THEN** each published payload retains the existing load number, sequence number, completion, and generation semantics

#### Scenario: Stale result is encountered
- **WHEN** a payload belongs to an older load generation
- **THEN** the system discards it without replacing the current generation's mesh or metadata

#### Scenario: Source face normals are transferred
- **WHEN** a normalized source `Trimesh` provides per-face `face_normals`
- **THEN** payload conversion preserves those normals in its required per-face normal array and the renderer uses them without recalculating geometric normals

#### Scenario: Payload visibility remains internal
- **WHEN** application code crosses a loader, controller, UI, adapter, or renderer boundary
- **THEN** it uses the internal payload representation without requiring or exposing `MeshPayload` as a public SCADview API

### Requirement: Public mesh creation behavior remains compatible
The system SHALL continue accepting the documented `create_mesh` return types
and SHALL perform payload conversion only after existing mesh normalization and
validation.

#### Scenario: Supported return type is loaded
- **WHEN** `create_mesh` returns a `Trimesh`, `Manifold`, feature mesh, or documented list or generator form
- **THEN** the system presents the same normalized geometry without requiring changes to the user module

#### Scenario: Invalid return value is loaded
- **WHEN** `create_mesh` returns an unsupported value or invalid geometry
- **THEN** the load fails through the existing error-result behavior rather than publishing a partial payload as successful

### Requirement: Rendering accepts payload geometry only
The system SHALL ensure that all loaded and built-in mesh geometry enters the
production rendering subsystem only as compact payloads or payload-derived arrays.
The rendering subsystem SHALL NOT accept, construct, reconstruct, import, or
type-check complete `Trimesh` objects.

#### Scenario: Loaded geometry reaches rendering
- **WHEN** the current-generation loader result is presented to the renderer
- **THEN** controller, UI, adapter, renderer, and drawable boundaries pass payload geometry without reconstructing a `Trimesh`

#### Scenario: Built-in geometry reaches rendering
- **WHEN** startup, loading, or base-axis geometry is presented to the renderer
- **THEN** it uses the same payload-only renderer boundary as loaded geometry

### Requirement: Built-in scene assets are supplied at composition
The system SHALL construct and normalize the complete set of startup, loading,
and base-axis geometry outside the rendering subsystem and SHALL inject that set
before renderer creation. The renderer SHALL remain responsible for GL lifecycle,
transforms, visibility, drawable composition, and draw ordering.

#### Scenario: Renderer is created
- **WHEN** application composition creates a renderer
- **THEN** the renderer receives a complete payload-based scene-assets set without constructing source geometry itself

#### Scenario: Loading state is displayed
- **WHEN** load status changes to loading
- **THEN** the renderer selects and draws the injected loading payload using its existing GL and visibility lifecycle

#### Scenario: Axis scale or visibility changes
- **WHEN** loaded-mesh scale or axis visibility changes
- **THEN** the renderer transforms or shows the injected base-axis payload without creating or mutating a `Trimesh`

### Requirement: Source mesh objects remain loader-owned
Within the load-display-export path, the system SHALL confine complete `Trimesh`
objects to source-geometry normalization and loader-owned export execution. The
normalized source SHALL remain in the loader process and SHALL NOT cross the
display result queue or become controller, UI, adapter, or renderer state. This
boundary SHALL NOT alter documented geometry-authoring APIs.

#### Scenario: Source mesh is normalized
- **WHEN** user-module or built-in source geometry is accepted
- **THEN** it is converted to a payload before crossing into queue, controller, UI, adapter, or renderer ownership

#### Scenario: Final source is retained
- **WHEN** a final successful non-debug single mesh is accepted for the current generation
- **THEN** the loader retains the normalized `Trimesh` source for export and publishes only its payload view to the display queue

#### Scenario: Debug or failed source is completed
- **WHEN** a debug list, failed result, or non-final intermediate result is processed
- **THEN** the loader does not publish that result as the export source

### Requirement: Rendering behavior is preserved
The compact-payload stage SHALL preserve the current observable rendering of
geometry, default and explicit mesh-level colors, transparency ordering, framing,
feature-debug lists, incremental results, and triangle-edge display.

#### Scenario: Opaque mesh is displayed
- **WHEN** an opaque payload is loaded
- **THEN** its geometry, flat shading, color, framing bounds, and optional triangle edges match the existing rendering path

#### Scenario: Transparent mesh list is displayed
- **WHEN** payloads with different colors and alpha values are loaded together
- **THEN** the renderer preserves global triangle sorting and each payload's mesh-level color

#### Scenario: Edge display is toggled
- **WHEN** the user enables edge display for a compact payload
- **THEN** all triangle boundaries are displayed with the same corner-marker semantics as the existing renderer

### Requirement: Export behavior is preserved from the source mesh
The system SHALL keep export available for the final successfully loaded,
non-debug mesh and SHALL export the retained normalized source `Trimesh` without
reconstructing it from `MeshPayload`. Export SHALL remain asynchronous to the UI
and SHALL preserve the existing supported formats and error reporting.

#### Scenario: Loaded mesh is exported
- **WHEN** the user exports a completed single-mesh load to a currently supported format
- **THEN** the loader exports the retained normalized source through the existing format-specific path with its original geometry, metadata, visuals, and color state

#### Scenario: Export is requested during a load
- **WHEN** the user requests export while a new load is active or no final source exists for the requested generation
- **THEN** the controller rejects or disables the request without blocking the UI or exporting stale source data

#### Scenario: Export completes after a reload begins
- **WHEN** an accepted export request is followed by a new load
- **THEN** the export result remains correlated to its request id and reports completion or a structured error without replacing the new generation's display state

#### Scenario: Export fails
- **WHEN** the exporter raises an expected file or format error
- **THEN** the loader returns a structured correlated error and the UI preserves existing error-reporting behavior

#### Scenario: Debug list is displayed
- **WHEN** the current result has debug-list status
- **THEN** export remains unavailable as in the existing interface

### Requirement: Fully indexed rendering is gated by evidence
The initial compact-payload stage SHALL retain the established triangle-corner
rendering behavior, and fully indexed GPU rendering SHALL remain deferred from
this change. If post-change measurements identify render expansion or upload as a
material remaining bottleneck, a separately reviewed follow-up SHALL define the
indexed design and require visual parity for edges, flat shading, transparency,
colors, and framing.

#### Scenario: Compact transfer meets the measured objective
- **WHEN** post-change measurements show that renderer indexing is not needed to address the measured bottleneck
- **THEN** fully indexed shader rendering remains deferred

#### Scenario: Indexed rendering is still justified
- **WHEN** post-change measurements show render expansion or upload remains a material bottleneck
- **THEN** indexed rendering is proposed as a separately reviewable stage with automated checks and human visual validation before adoption
