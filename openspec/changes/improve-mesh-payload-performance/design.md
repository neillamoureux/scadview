## Context

See `proposal.md` for motivation. User modules execute in a loader process, where
supported return values are normalized to `Trimesh` instances. `LoadResult`
currently sends those instances through a bounded multiprocessing queue. The main
process retains the received object for export and passes it through wx and the GL
adapter to the renderer.

The renderer reads expanded triangle positions and per-face cross products from
`Trimesh`, repeats normals and mesh-level colors for every triangle corner, and
generates barycentric corner markers for edge display. Transparent meshes are
combined and resorted by triangle whenever the view changes. These per-corner
requirements mean that directly indexing shared positions cannot preserve current
flat normals and edge markers without a shader or data-layout change.

The process boundary must remain typed and isolated from wx and GL concerns. The
public `create_mesh` contract remains `Trimesh`, `Manifold`, feature mesh, and the
documented list and generator forms.

## Goals / Non-Goals

**Goals:**

- Establish comparable baseline and post-change measurements before selecting
  deeper renderer work.
- Replace complete `Trimesh` objects on the result queue with a compact,
  validation-friendly internal representation.
- Move conversion work that does not require a GL context into the loader process.
- Preserve existing queue freshness, rendering, framing, and on-demand export
  behavior.
- Create a stable renderer input seam that permits a later indexed implementation
  without exposing the payload as public API.

**Non-Goals:**

- Shared-memory allocation or cross-process buffer lifetime management.
- GPU instancing or optimization of mesh construction and boolean operations.
- Smooth shading, geometric edge extraction, materials, textures, or per-face and
  per-vertex colors not currently rendered by SCADview.
- A fully indexed shader pipeline unless a separately reviewed follow-up is
  justified by the measurements from this change.

## Decisions

### Measure before and after the compact stage

Add a repeatable benchmark harness before changing production behavior. It will
exercise at least a deterministic high-sharing triangular mesh at multiple sizes,
a mixed opaque/transparent list, and a representative large project example. It
will record mesh vertex/face counts, pickle size, conversion and round-trip time,
supported peak-memory measurements, renderer preparation/upload time, and time to
the first frame. Absolute timing assertions will not run in normal CI; structural
and size properties of the harness remain testable.

After integration, run the same cases and preserve the environment and results in
the change evidence. The indexed-renderer gate asks whether CPU expansion, upload,
or retained render buffers remain a material contributor after transport is
compacted; it does not assume the answer.

Alternative: redesign the renderer first. Rejected because no current measurement
identifies the renderer rather than serialization as the dominant cost.

### Use a neutral internal payload model

Place the payload and pure conversions in an internal module outside the UI,
controller, loader-process orchestration, and GL renderer packages. This keeps the
payload usable on both sides of the process boundary without reversing existing
dependencies.

One payload represents one mesh and contains:

- C-contiguous `float32` vertices with shape `(N, 3)`;
- C-contiguous `uint32` triangle faces with shape `(M, 3)`;
- C-contiguous `float32` per-face normals with shape `(M, 3)`;
- one optional RGBA mesh-level color in the renderer's fixed-width form;
- compact bounds and scale summaries used for framing and axes.

Payload construction validates shapes, finite values, and that face indices are
non-negative, in range, and representable as `uint32` before casting. It copies
the arrays so later mutation of a source mesh cannot alter a queued result. A list
result remains a list of payloads, preserving order and the existing distinction
between normal and debug status. Edge-marker arrays and repeated colors are not
transported because they are deterministic render data.

Alternative: put the model in the renderer package. Rejected because the loader
would then depend outward on rendering. Alternative: serialize a reduced
`Trimesh`. Rejected because it preserves library-object coupling and gives less
control over cached state and fixed-width representation.

### Convert after normalization and before publication

The loader continues validating user results, resolving feature meshes, converting
`Manifold`, selecting debug sources, and assigning debug colors in the current
order. It then converts each resulting `Trimesh` to a payload immediately before
constructing `LoadResult`. Queue size, replacement behavior, generation checks,
incremental sequence numbers, errors, feature states, and parameters stay intact.

This location removes complete `Trimesh` instances from process transfer while
leaving the user-facing module contract untouched.

### Retain payloads and reconstruct exports on demand

The controller retains the latest payload rather than eagerly rebuilding a
`Trimesh`. UI export enablement checks whether an exportable final payload exists.
On export, a pure conversion creates a non-processing `Trimesh` from vertices and
faces and restores SCADview mesh-level color metadata before invoking the existing
format-specific exporter. Debug-list status remains non-exportable.

This preserves documented geometric export behavior while avoiding the normal
memory cost of both payload and reconstructed mesh. SCADview does not currently
render or document preservation of arbitrary materials, textures, or non-SCADview
metadata, so those are not added to the transport contract.

Alternative: retain a second complete export mesh in the loader process and add an
export command. Rejected because it increases process protocol and file-operation
complexity and keeps the large object alive after every load.

### Preserve the triangle-corner renderer in the initial stage

The renderer accepts payloads at its service boundary and initially derives
triangle positions, repeated face normals, per-corner colors, and barycentric edge
markers when creating GL buffers. Opaque buffer creation may remain lazy;
transparent triangle sorting remains global and rebuilds sorted corner data as it
does today. Bounds and scale come from payload summaries rather than rescanning or
reconstructing a mesh.

A naïve index buffer cannot share positions while retaining both flat face normals
and barycentric corner attributes. If post-change evidence justifies a fully
indexed follow-up, that design should evaluate geometry-shader-generated normals
and barycentrics or an equivalent portable technique, update sorted index buffers
for transparency, and preserve colors across combined transparent meshes. It must
pass automated geometry tests and human visual checks on supported platforms
before replacing the established path.

Alternative: adopt shared position indexing immediately and use per-vertex normals
and vertex identifiers for edges. Rejected because it changes shading and cannot
reproduce corner markers for vertices shared by multiple triangles.

## Risks / Trade-offs

- [Float and index narrowing can overflow or subtly alter geometry] -> Validate
  before casting, fail through the existing load error path, and compare payload
  geometry with normalized source meshes in tests.
- [On-demand export temporarily duplicates geometry] -> Limit reconstruction to
  explicit export and release it after the exporter returns.
- [A compact payload may improve pickle size but not first-frame latency] -> Keep
  measurement as an acceptance activity and defer shader work unless the remaining
  cost is material.
- [Renderer conversion can create large temporary arrays] -> Build buffers from
  bounded, contiguous arrays, avoid chained copies, and use benchmark memory data
  to identify remaining peaks.
- [Transparency or edge visuals can regress during seam changes] -> Cover ordering
  and buffer semantics with tests and perform screenshot/manual comparisons for
  representative opaque, transparent, and debug scenes.
- [Queue cancellation can retain obsolete payload memory briefly] -> Preserve and
  test the existing bounded queue and generation-discard rules.

## Migration Plan

1. Add the benchmark harness and capture the current path's baseline.
2. Add the internal payload model and pure round-trip conversions behind tests.
3. Change loader results, controller ownership, and export reconstruction together
   so no mixed process protocol is shipped.
4. Adapt the renderer seam while retaining its established corner-buffer strategy.
5. Run automated validation, repeat measurements, and complete human visual checks.
6. Record the indexed-renderer gate outcome; pursue it only through a separately
   reviewed follow-up if justified.

The payload is internal and persisted only in memory, so no data migration or
compatibility bridge is required. Rollback consists of reverting the process
protocol, controller, and renderer seam as one change.
