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

The renderer package also constructs its startup mesh, loading placeholder, and
base axes with `Trimesh`. That use is independent of loaded-user-mesh transfer but
would keep the renderer coupled to the source geometry library after its public
load seam changes. Built-in geometry therefore needs the same one-way conversion
at a boundary outside rendering.

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
- Preserve existing queue freshness, rendering, framing, and lossless export
  behavior without transferring the source mesh through the display queue.
- Make all production renderer inputs payload-only and keep production modules
  under `scadview.render` independent of `Trimesh`.
- Inject built-in geometry as a coherent scene-assets value while retaining
  renderer ownership of GL resources, transforms, visibility, drawables, and draw
  ordering.
- Create a stable seam that permits a later indexed implementation without
  exposing the payload as public API.

**Non-Goals:**

- Shared-memory allocation or cross-process buffer lifetime management.
- GPU instancing or optimization of mesh construction and boolean operations.
- Smooth shading, geometric edge extraction, materials, textures, or per-face and
  per-vertex colors not currently rendered by SCADview.
- Removing `Trimesh` from public geometry-authoring APIs, feature operations,
  source normalization, or loader-owned export execution.
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

### Confine Trimesh to source normalization and loader-owned export

Within the runtime load-display-export path, `Trimesh` is allowed inside source
normalization and loader-owned export execution. Source normalization includes
user-module results, `Manifold` conversion, feature resolution, and built-in scene
geometry supplied by resource builders. The loader retains the final normalized
user source and derives a payload view before publication. The source mesh does
not enter the display queue, controller, UI, adapter, renderer-factory, or
renderer interfaces. Built-in assets are converted to payloads before renderer
composition.

The public geometry-authoring APIs continue returning and operating on `Trimesh`
where documented; removing that project-wide dependency is unrelated to this
change. Tests may also use Trimesh factories as fixture producers, provided they
convert the result before exercising a production renderer seam.

Alternative: tolerate `Trimesh` for renderer-owned utility meshes. Rejected
because it leaves two geometry representations inside rendering and weakens the
boundary the payload is intended to establish.

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

### Retain payloads and export from the loader-owned source

The controller retains the latest payload for rendering, while the loader retains
only the final successful, non-debug normalized `Trimesh` for export. The
controller sends an `ExportCommand` containing a request id, generation, and path
through a command channel. The loader performs export against the retained source
on a worker thread and returns a correlated, structured `ExportResult` through a
dedicated reliable result queue. The UI polls that queue and disables duplicate
requests while one is pending. Debug-list status remains non-exportable.

This preserves documented geometric export behavior while avoiding transfer of a
second complete mesh to the main process. SCADview does not currently render or
document preservation of arbitrary materials, textures, or non-SCADview metadata
in the renderer payload; the retained source remains authoritative for export.

Alternative: reconstruct an export mesh from the payload. Rejected because fixed
width payload fields lose coordinate precision, color precision, arbitrary
metadata, visual state, and future `Trimesh` attributes. Alternative: send and
retain a complete `Trimesh` in the main process. Rejected because it restores the
serialization, unpickling, memory pressure, and UI pause that this change targets.

The export protocol uses a separate reliable queue rather than the bounded
latest-wins display queue. A source is published for export only when a final
successful non-list result is accepted for the current generation. Starting a new
load invalidates the previous source for new export requests, while an already
accepted export completes and reports its own request id. Shutdown stops accepting
new export work and applies the existing bounded process-termination policy if an
export cannot finish.

### Inject built-in geometry as SceneAssets

Introduce an immutable `SceneAssets` value containing payloads for the startup
mesh, loading placeholder, and unscaled base axes. The application composition
path constructs these assets once, normalizes any existing resource-builder output
to payloads, and injects the complete value into `RendererFactory`, which passes it
to each `Renderer`. Neither factory nor renderer constructs source geometry or
accepts a fallback `Trimesh`.

The renderer creates drawables and GL buffers from the injected payloads. It owns
selection of the startup or loading drawable, axis visibility, and axis scaling.
Scaling uses renderer-owned transforms or payload-neutral array operations rather
than copying and mutating a `Trimesh`. Asset providers own geometry shape and
source-library conversion; the renderer owns presentation and GPU lifecycle.

Requiring a complete `SceneAssets` value makes missing built-ins fail during
composition rather than midway through rendering and keeps tests explicit.

Alternative: let the renderer call a scene-asset factory. Rejected because it
hides construction and source-library dependencies behind the renderer boundary.
Alternative: inject unrelated payload parameters. Rejected because a named,
immutable aggregate makes asset completeness and ownership clear.

### Keep the renderer payload-only in the initial stage

Every production API under `scadview.render` accepts payloads, payload lists, or
payload-derived arrays for mesh geometry. Payload-neutral renderee names and
helpers replace Trimesh-specific interfaces, and bounds-to-corners calculations
use local NumPy logic. No production renderer module imports, type-checks,
constructs, or reconstructs `Trimesh`.

The initial implementation still derives triangle positions, repeated face
normals, per-corner colors, and barycentric edge markers when creating GL buffers.
Opaque buffer creation may remain lazy; transparent triangle sorting remains
global and rebuilds sorted corner data as it does today. Bounds and scale come
from payload summaries rather than rescanning or reconstructing a mesh. Renderer
continues to own GL context and buffer lifetime, transforms, visibility, drawable
composition, and draw ordering.

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
- [The loader retains one complete source mesh] -> Retain only the final
  successful non-debug source, measure child-process RSS, and revisit spooling
  only if retained memory is material.
- [Export protocol races with reload or shutdown] -> Correlate request ids,
  require generation-aware source selection, use a reliable result queue, and
  test cancellation, process death, and shutdown.
- [A compact payload may improve pickle size but not first-frame latency] -> Keep
  measurement as an acceptance activity and defer shader work unless the remaining
  cost is material.
- [Renderer conversion can create large temporary arrays] -> Build buffers from
  bounded, contiguous arrays, avoid chained copies, and use benchmark memory data
  to identify remaining peaks.
- [Transparency or edge visuals can regress during seam changes] -> Cover ordering
  and buffer semantics with tests and perform screenshot/manual comparisons for
  representative opaque, transparent, and debug scenes.
- [Injecting built-in assets can change startup, loading, or axis presentation] ->
  Convert the existing resource geometry outside rendering, compare bounds and
  topology, and include all built-ins in visual validation.
- [Scene asset injection broadens constructor changes] -> Pass one immutable
  aggregate through the composition root and update renderer tests to supply
  explicit lightweight fixtures.
- [Queue cancellation can retain obsolete payload memory briefly] -> Preserve and
  test the existing bounded queue and generation-discard rules.

## Migration Plan

1. Add the benchmark harness and capture the current path's baseline.
2. Add the internal payload model and pure round-trip conversions behind tests.
3. Change loader results, controller ownership, and export protocol together so
   no mixed process protocol is shipped.
4. Build and inject payload-based `SceneAssets` from outside rendering.
5. Adapt the adapter, renderer, and renderee seams to payload-only inputs while
   retaining the established corner-buffer strategy and renderer responsibilities.
6. Run automated validation, repeat measurements, and complete human visual checks.
7. Record the indexed-renderer gate outcome; pursue it only through a separately
   reviewed follow-up if justified.

The payload is internal and persisted only in memory, so no data migration or
compatibility bridge is required. Rollback consists of reverting the process
protocol, controller, and renderer seam as one change.
