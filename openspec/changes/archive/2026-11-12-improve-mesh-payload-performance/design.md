## Context

See `proposal.md` for motivation. At the start of this change, user modules ran in
a loader process and their return values were normalized to `Trimesh` instances.
`LoadResult` sent those instances through a bounded multiprocessing queue, and the
main process retained them for export and passed them through wx to the renderer.
The decisions below replace that architecture with native loader-owned sources
and payload-only display boundaries.

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
- Isolating arbitrary user-module process state such as `sys.modules`, `sys.path`,
  or user-defined module globals across overlapping loads. Feature capture state
  is isolated for this change; broader module-session isolation is deferred to a
  separately reviewed follow-up that can choose between serialized execution and
  per-generation child processes.

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

Retained-source memory reports keep source classification separate from
measurement availability. `retained_source_kind` identifies a single retained
source or a list/debug result with no retained source. A separate support field is
true after a successful RSS measurement, false with a structured reason after an
attempted but unavailable measurement, and null when measurement is disabled or
not applicable. Numeric RSS values are present only for successful measurements,
including a valid zero delta.

Alternative: redesign the renderer first. Rejected because no current measurement
identifies the renderer rather than serialization as the dominant cost.

After Group 13 removed source signatures, the user authorized updating the existing
benchmark harness and tests. Report version 5 removes signature measurements and
counts both progress and fresh final payload preparation in conversion time. The
counterfactual Trimesh path performs no payload conversions. The existing synthetic
workloads prepare progress and final results but transfer only the final result;
the aggregate display time sums separately measured stages, not a live GUI load.
Generator coalescing, native Manifold workloads, and GUI polling are not measured.
Export timing uses the worker's current in-process completion queue and excludes
controller/GUI polling; it is not the latency of the entire export protocol.
Historical evidence and new benchmark workloads remain deferred.

### Keep native sources inside loader ownership

Within the runtime load-display-export path, native `Trimesh` and `Manifold`
values remain inside source selection and loader-owned export execution. Feature
resolution preserves native types. The loader retains the final native
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

`MeshPayload` is an internal transport and rendering model, not a public
SCADview API. Its per-face normal array is required and is populated from the
source mesh's `Trimesh.face_normals` during payload conversion. For Manifold,
float64 triangle cross products are normalized with the same degeneracy threshold
as the existing Trimesh adapter; vertex properties are not treated as normals. The
renderer respects those supplied normals and does not recalculate them. This
preserves client-provided `face_normals` on Trimesh and geometric shading on
Manifold without creating a temporary Trimesh.

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

### Convert native sources before publication

The loader continues validating user results, resolving feature meshes,
selecting debug sources, and assigning debug colors in the current order.
It converts each selected native source directly to a payload immediately before
constructing `LoadResult`. Queue size, replacement behavior, generation checks,
incremental sequence numbers, errors, feature states, and parameters stay intact.

This location removes complete `Trimesh` instances from process transfer while
leaving the user-facing module contract untouched.

### Coalesce incremental sources before payload conversion

The generator producer resolves sources, selects debug geometry, and captures
feature metadata in its own thread. Before resuming the generator it copies
mutable Trimesh sources (including supplied face normals) into a one-slot
replacement channel; immutable Manifold values are handed off by reference.
A conversion consumer takes the newest pending source and produces payloads;
replaced pending sources never become payloads or display results. Original yield
indices remain sequence numbers, while revisions count publications.

Copying on the producer while the generator is suspended preserves generators
that reuse mutable meshes and lists. This costs a copy per Trimesh yield but avoids
an unsafe background copy racing generator mutation. Independently spawned user
threads must not mutate sources during the yield handoff. Feature capture remains
producer-owned because its context is thread-local.

Completion closes and drains the source channel, then finalization derives the
terminal payload from the final source after generator exhaustion, including
post-yield mutations and late feature declarations. Retain the original last
yielded object, not a resolved copy of its list. Always prepare it again once at
successful finalization; do not hash sources, compare Manifold identities, or reuse
a progress payload to avoid conversion. Clients should avoid duplicate yields when
performance matters. Only that terminal snapshot is exportable.

Conversion failure closes pending work and publishes its terminal error without
waiting for the producer to yield or return. Use the existing terminal claim shared
with cancellation, and the captured progress metadata rather than reading feature
state from the converter thread. The producer's eventual completion cannot publish
another terminal result. Benchmark updates remain deferred.

At both result queue handoffs, a receiver may remove the queued result after a
sender observes a full queue. If removal then finds an empty queue, retry putting
the result; repeat replacement if the slot fills again. Serialize worker senders
while comparing and replacing queued generations so an older result cannot evict
a newer one. The loader command loop remains the sole process-queue sender.

### Make load state explicit with a result envelope

The loader session should expose result state explicitly rather than requiring
consumers to infer meaning from payload shape, sequence numbers, and feature
flags. The internal envelope should contain equivalent fields to:

```python
@dataclass(frozen=True)
class LoadResult:
    load_number: int
    generation: int
    sequence_number: int
    revision: int
    phase: LoadPhase
    payload: MeshPayload | list[MeshPayload] | None
    exportable: bool
    error: LoadError | None
    features: list[FeatureState]
    parameters: list[CreateMeshParameter]
```

The exact names may follow existing conventions, but the semantics are required:
`phase` distinguishes progress, final, error, and cancellation; `revision`
identifies a new display state even when sequence numbers repeat; `exportable`
describes the effective result rather than requested debug mode; and `payload`
remains the only mesh data exposed outside the loader process. The controller
applies each accepted envelope as one state transition, and the UI uses its
explicit phase, revision, and exportability instead of reconstructing those
values independently.

`LoadResult` is immutable after construction. `CANCELLED` is the sole cancellation
phase member, `payload` is the sole mesh-bearing envelope field, and terminal
completion is a read-only property derived from `phase`; there are no legacy
phase, mesh, or stored-completion aliases.

Effective debug state is assigned by the loader when it selects the result source;
consumers never infer it from the payload container. The existing contract is
preserved: a single payload is a normal result that may be exportable, while any
list payload is an explicitly debug result and is non-exportable. A debug list may
contain one or many payloads, but its debug status is an explicit envelope field,
not a consequence rediscovered by the controller, UI, or renderer.

### Retain payloads and export from the loader-owned source

The controller retains the latest payload for rendering, while the loader retains
only the final successful, non-debug native `Trimesh` or `Manifold` for export. The
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

The loader accepts an export by copying a retained Trimesh or adapting a retained
Manifold through the existing `manifold_to_trimesh` helper before starting the
export worker. The result is an isolated point-in-time value of the source geometry,
visuals, attributes, and metadata; replacing or mutating the user-retained source
after acceptance cannot change the export. Copying occurs synchronously in the
loader command loop so a subsequently queued reload cannot start before the
snapshot exists, while the main process and wx event loop remain asynchronous.
Only accepted exports pay the temporary copy cost, and reaping the export worker
releases its snapshot. A copy failure produces a correlated structured export
error and starts no worker.

This source-native revision supersedes the normalized-Trimesh retention decisions
in tasks 8.2 and 9.2. Manifold vertex properties retain their existing export
interpretation through the unchanged adapter; display still uses mesh-level color
and applies debug palette colors to payloads. Trimesh metadata, visuals, precision,
and post-yield mutation behavior remain unchanged. Native property vertices may
remain duplicated for display, provided triangle geometry and shading match.
Same-machine local diagnostics compare the committed and candidate loader paths
on `examples/messner_mani.py`. Retain the candidate only if meaningfully faster and
correct. Benchmark harness and evidence-file updates remain deferred.
Human GUI validation must still check incremental final display, debug-list colors,
framing, transparency, and export from the displayed final Manifold.

Round-four review identified that the existing export adapter can merge nearby
vertices and collapse very thin Manifold geometry, unlike native display. The
user explicitly limited item 4 to documenting this caveat in `docs/create_mesh.md`;
changing the adapter and adding thin-solid export tests are deferred.

Snapshot creation and exporter invocation are isolated in named asynchronous
protocol-boundary adapters. The adapters catch `Exception`, but not
`BaseException`, because copying and exporter plugins can fail with exception
types the application cannot enumerate and an uncaught boundary failure would
strand the request. Each catch covers only its external operation and converts the
failure to a structured export error; the terminal result is published exactly
once outside the adapter.

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
  require generation-aware source selection, copy the source at acceptance, use a
  reliable result queue, and test mutation, cancellation, process death, and
  shutdown.
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
2. Add the internal payload model and one-way source-to-payload conversion behind
   tests; loader-owned export remains source-based and does not reconstruct a
   source mesh from a payload.
3. Change loader results, controller ownership, and export protocol together so
   no mixed process protocol is shipped.
4. Introduce the explicit load-result envelope and final-snapshot state model.
5. Build and inject payload-based `SceneAssets` from outside rendering.
6. Adapt the adapter, renderer, and renderee seams to payload-only inputs while
   retaining the established corner-buffer strategy and renderer responsibilities.
7. Run automated validation, repeat measurements, and complete human visual checks.
8. Record the indexed-renderer gate outcome; pursue it only through a separately
   reviewed follow-up if justified.

The broader question of isolating arbitrary user-module state across overlapping
loads is recorded as a follow-up design decision rather than silently expanded into
this change.

The payload is internal and persisted only in memory, so no data migration or
compatibility bridge is required. Rollback consists of reverting the process
protocol, controller, and renderer seam as one change.
