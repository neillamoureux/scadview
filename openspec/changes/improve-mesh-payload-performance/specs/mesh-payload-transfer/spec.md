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
rendering and export. A successful mesh result SHALL NOT contain a complete
`Trimesh` object.

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

### Requirement: Export behavior is preserved
The system SHALL keep export available for the final successfully loaded,
non-debug mesh and SHALL reconstruct an exportable mesh only when export needs
one. The reconstructed mesh SHALL preserve the loaded vertices, triangle faces,
and SCADview mesh-level color metadata without changing the available export
formats or existing error reporting.

#### Scenario: Loaded mesh is exported
- **WHEN** the user exports a completed single-mesh load to a currently supported format
- **THEN** the exported mesh has geometry equivalent to the normalized loaded mesh and follows the existing format-specific export path

#### Scenario: Debug list is displayed
- **WHEN** the current result has debug-list status
- **THEN** export remains unavailable as in the existing interface

### Requirement: Fully indexed rendering is gated by evidence
The initial compact-payload stage SHALL retain the established triangle-corner
rendering behavior. A fully indexed GPU representation SHALL NOT be adopted by
this change unless post-change measurements identify render expansion or upload
as a material remaining bottleneck and visual validation demonstrates parity for
edges, flat shading, transparency, colors, and framing.

#### Scenario: Compact transfer meets the measured objective
- **WHEN** post-change measurements show that renderer indexing is not needed to address the measured bottleneck
- **THEN** fully indexed shader rendering remains deferred

#### Scenario: Indexed rendering is still justified
- **WHEN** post-change measurements show render expansion or upload remains a material bottleneck
- **THEN** indexed rendering is proposed as a separately reviewable stage with automated checks and human visual validation before adoption
