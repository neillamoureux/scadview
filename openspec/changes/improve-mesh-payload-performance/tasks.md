## 1. Establish Performance Baseline

- [x] 1.1 Create stubs for a repeatable mesh-transfer benchmark harness with deterministic high-sharing, mixed-transparency, and representative large-model cases; verify the runner discovers every case and exposes the planned metric names.
- [x] 1.2 Add benchmark-harness tests for case sizing, environment metadata, serialized-size reporting, timing fields, and optional peak-memory fields; run the targeted tests and confirm they fail for the unimplemented measurements.
- [x] 1.3 Implement measurement of the existing `Trimesh` path and record the baseline command, environment, vertex/face counts, pickle size, conversion and queue round-trip time, supported peak memory, renderer preparation/upload time, and first-frame time; verify a repeated run emits complete comparable results without enforcing noisy absolute timings in CI.

## 2. Add the Compact Payload Model

- [x] 2.1 Create typed stubs in a neutral internal module for the single-mesh payload, source-to-payload conversion, and payload-to-export-mesh conversion; verify imports and static analysis resolve without adding a public top-level export.
- [x] 2.2 Add failing unit tests for array shapes, `float32`/`uint32` dtypes, C contiguity and copying, normals, default and explicit RGBA color, bounds, scale, empty geometry, round-trip geometry/color, invalid indices, overflow, and non-finite values; run the targeted tests and confirm the expected red state.
- [x] 2.3 Implement payload validation and conversions after the failing tests exist; verify all payload unit tests pass and pickle-size tests show that representative compact payloads contain no `Trimesh` object and are smaller than the measured source representation.

## 3. Change Loader Result Transport

- [x] 3.1 Update internal result and queue type stubs to carry one payload, a payload list, or no mesh while retaining load metadata and debug-status semantics; verify type checking reaches the intended incomplete conversion seam.
- [x] 3.2 Add failing loader and queue tests for single meshes, lists, feature-debug colors, generators, completion/error results, bounded-queue replacement, cancellation, and stale generations; run the targeted tests and confirm failures are caused by results still carrying `Trimesh` values.
- [x] 3.3 Convert normalized and validated meshes to payloads immediately before publication without changing normalization order or metadata; verify loader/queue tests pass, an actual multiprocessing round trip contains equivalent payload geometry with no complete `Trimesh` instance, and source objects do not enter controller ownership.

## 4. Retain Payloads and Preserve Export

- [x] 4.1 Create controller and UI boundary stubs for retaining payload results and detecting exportable final payloads; verify static analysis identifies all remaining `current_mesh` assumptions. (Export reconstruction is superseded by Group 8.)
- [x] 4.2 Add controller/UI tests for current-generation ownership, stale-result rejection, export enablement, debug-list non-exportability, supported-format dispatch, and exporter errors; run the targeted tests and confirm the expected red state. (Lossless source-fidelity coverage is superseded by Group 8.)
- [x] 4.3 Implement payload ownership and preserve the existing export dispatch seam; verify controller and UI tests pass and no source mesh becomes retained controller, UI, or renderer state. (Loader-owned export is superseded by Group 8.)

## 5. Externalize and Inject Built-in Scene Assets

- [x] 5.1 Create typed stubs for an immutable `SceneAssets` aggregate, an external built-in asset provider, and constructor injection through application composition, renderer factory, and renderer; verify static analysis exposes every renderer-owned startup, loading, and axis geometry construction site.
- [x] 5.2 Add failing tests for complete scene-asset construction, source-to-payload normalization, factory/renderer injection, startup and loading selection, and base-axis scale/visibility behavior; run the targeted tests and confirm failures are caused by built-ins still being constructed inside the renderer.
- [x] 5.3 Implement built-in startup, loading, and unscaled base-axis construction outside `scadview.render`, normalize each source to a payload before injection, and move axis sizing to renderer-owned transforms or payload-neutral operations; verify scene-asset and renderer tests pass with no source geometry constructor crossing the renderer boundary.

## 6. Make Rendering Payload-only Without Changing Visual Semantics

- [x] 6.1 Create payload-only renderer, GL-adapter, and payload-neutral renderee stubs that accept payloads or derived arrays and expose payload bounds/scale while retaining the current triangle-corner buffer strategy; verify static analysis identifies every remaining production `Trimesh` reference under `scadview.render`.
- [x] 6.2 Add failing renderer tests for dependency isolation, indexed-to-triangle expansion, flat per-face normals, one mesh-level color, opaque lazy upload, global transparent sorting with multiple colors, framing/scale, empty lists, barycentric edge markers, and injected built-in drawables; run the targeted tests and confirm failures are due to the old renderer seam.
- [x] 6.3 Implement payload-based render preparation with bounded contiguous temporaries and unchanged alpha sorting and edge-marker semantics while retaining renderer ownership of GL resources, transforms, visibility, drawables, and draw ordering; verify renderer tests pass, production `scadview.render` modules contain no `Trimesh` import or reconstruction, and renderer-facing signatures are payload-only.

## 7. Validate and Apply the Indexed-Renderer Gate

- [x] 7.1 Run formatting, linting, type checks, targeted scene-asset/loader/controller/renderer tests, and the full project preflight; verify every command passes and inspect the final diff for architectural boundary violations or unrelated changes.
- [x] 7.2 Repeat the baseline benchmark cases on the compact path and record comparable before-and-after results; verify the report identifies whether serialization, payload conversion, renderer expansion, upload, or retained buffers dominate remaining cost.
- [x] 7.3 Manually compare startup, loading, base-axis, opaque, transparent multi-mesh, feature-debug, incremental, edge-on/off, and framing scenes on supported GUI/OpenGL environments; verify visual parity and record the tested platforms because automated checks cannot establish visual correctness.
- [x] 7.4 Record the indexed-renderer gate decision from benchmark and visual evidence; verify fully indexed shader work remains deferred, or open a separately reviewable OpenSpec change with explicit portability and visual-acceptance criteria if renderer expansion/upload remains a material bottleneck.

## 8. Restore Lossless Loader-Owned Export

- [x] 8.1 Add typed export command/result models and a dedicated reliable export-result queue; preserve request ids, generations, structured errors, and existing process lifecycle semantics.
- [x] 8.2 Retain only the final successful non-debug normalized `Trimesh` in the loader process, invalidate it on newer generations, and publish only its `MeshPayload` view through the latest-wins display queue; remove `payload_to_trimesh` from production export flow.
- [x] 8.3 Implement asynchronous controller/UI export request, polling, duplicate-request suppression, stale-source handling, and error display without blocking the wx event loop.
- [x] 8.4 Add fidelity tests proving exports use the retained source, including float precision, SCADview color precision, metadata, visuals, supported-format dispatch, and exporter errors.
- [x] 8.5 Add concurrency and lifecycle tests for incremental results, reload during export, stale generations, queue behavior, loader failure, process death, and shutdown.
- [x] 8.6 Repeat performance and memory measurements, including retained loader-process RSS and export latency, then update the benchmark evidence and PR description.

## 9. Make Load State Explicit

- [x] 9.1 Add typed phase, revision, exportability, and structured terminal-error fields to the internal load-result envelope while preserving generation, sequence, feature, and parameter metadata.
- [x] 9.2 Introduce a loader-owned final snapshot that atomically pairs the retained normalized source `Trimesh` with its final `MeshPayload`; make finalization the only path that publishes exportable state.
- [x] 9.3 Update loader, controller, UI, and renderer-adjacent consumers to apply explicit result envelopes as state transitions instead of inferring finality or exportability from payload shape, sequence numbers, flags, or status.
- [x] 9.4 Add regression tests for progress, final, error, and cancellation phases; independent revisions; single-mesh and debug-list exportability; stale generations; and generator finalization/source-payload alignment.
- [x] 9.5 Run the affected suite, full preflight, and OpenSpec validation; confirm no public API or payload-only renderer boundary changes and update the decision evidence.
