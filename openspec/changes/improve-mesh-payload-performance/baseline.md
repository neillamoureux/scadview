## Mesh-transfer performance evidence, methodology version 3

### Requirement status and chronology

The OpenSpec scenario requiring a valid baseline before transport changes is
**unmet**. Commit `288f903` recorded the first measurements on 2026-09-11 at
16:41 MDT, before payload implementation began in `100d566` at 16:48 MDT, but
that harness generated degenerate faces and did not measure the production
publication path. Later corrections in `c8fa1b4` and `1a595cd` were made after
the payload implementation and therefore cannot retroactively satisfy the
chronological baseline requirement.

The results below were captured on 2026-09-13 after implementation. They compare
two representations in the same version of the corrected harness:

- `payload` measures the current publication path, including payload conversion,
  the two production source-signature passes, progress/final `LoadResult`
  construction, final-snapshot work, typed queue transfer, and payload rendering;
- `trimesh` is a benchmark-only counterfactual that performs the same signature
  and envelope stages but transfers complete source meshes and uses the former
  renderer preparation algorithm.

This is useful diagnostic evidence, but it is not a chronological before/after
comparison and must not be used to claim that the pre-change baseline acceptance
scenario passed.

### Commands and environment

Each command was run twice, serially:

```console
uv run --no-sync python -m tools.mesh_transfer_benchmark --path trimesh --output /tmp/scadview-f9-final-trimesh-<N>.json
uv run --no-sync python -m tools.mesh_transfer_benchmark --path payload --output /tmp/scadview-f9-final-payload-<N>.json
```

All four reports identify benchmark version 3 and
`same-version-counterfactual`. The environment was macOS 26.6.2 x86_64 with
CPython 3.11.13, NumPy 2.3.4, Trimesh 4.9.0, ModernGL 5.12.0, and the `spawn`
multiprocessing start method.

### Measured path and aggregate definition

Deterministic source meshes are created before the measured publication stages.
The benchmark starts a child process, supplies those fixture meshes during
process startup, and excludes that startup/setup transfer because the production
loader is long-lived. In the child, publication uses the production signature
and final-snapshot helpers. The payload path publishes the actual final
`LoadResult` through `MpLoadQueue`; the counterfactual uses the same typed queue
wrapper with a benchmark-only Trimesh envelope. The child signals readiness
before the parent starts `child_to_main_transfer_ms`, so that metric measures the
trigger plus one actual child-to-main queue transfer and unpickle.

`pickle_size_bytes` is the standalone serialized size of the complete final
envelope. `loader_publication_ms` is mechanically composed as:

```text
payload_conversion_ms
+ source_signature_ms
+ envelope_finalization_ms
```

`post_mesh_creation_to_first_frame_ms` is mechanically composed as:

```text
loader_publication_ms
+ child_to_main_transfer_ms
+ renderer_preparation_ms
+ renderer_upload_ms
+ first_frame_ms
```

The benchmark records cold standalone GL context and shader-program creation as
`gpu_context_shader_setup_ms`. That setup occurs once during application startup,
not during normal mesh replacement, so it is explicitly excluded from the
post-creation aggregate. Each benchmark case creates a fresh standalone context
only to keep cases isolated; upload and first draw are measured after the context
and shader program are ready and are synchronized with `Context.finish()`.

Python allocation peaks are process-scoped: `loader_publication_peak_memory_bytes`
comes from `tracemalloc` in the publication child, while
`main_process_peak_memory_bytes` covers the main benchmark/render path. They are
reported separately rather than combined into a misleading process-wide peak.

### Publication and process-transfer results

All times are milliseconds and envelope sizes are bytes. `Sign` is the combined
time for the two production signature passes; `Finalize` covers progress/final
envelopes and final snapshot work.

| Case | Path/run | Meshes | Vertices | Faces | Envelope bytes | Convert | Sign | Finalize | Publication | Child→main |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| high-sharing-small | Trimesh 1 | 1 | 1,089 | 2,048 | 330,805 | 0.000 | 1.938 | 0.010 | 1.948 | 1.659 |
| high-sharing-small | Trimesh 2 | 1 | 1,089 | 2,048 | 330,805 | 0.000 | 1.964 | 0.010 | 1.974 | 1.556 |
| high-sharing-small | Payload 1 | 1 | 1,089 | 2,048 | 62,896 | 1.605 | 0.900 | 0.022 | 2.527 | 1.063 |
| high-sharing-small | Payload 2 | 1 | 1,089 | 2,048 | 62,896 | 1.623 | 0.900 | 0.022 | 2.545 | 1.006 |
| high-sharing-large | Trimesh 1 | 1 | 16,641 | 32,768 | 5,250,640 | 0.000 | 18.834 | 0.020 | 18.854 | 9.022 |
| high-sharing-large | Trimesh 2 | 1 | 16,641 | 32,768 | 5,250,640 | 0.000 | 18.075 | 0.011 | 18.086 | 8.305 |
| high-sharing-large | Payload 1 | 1 | 16,641 | 32,768 | 986,827 | 9.712 | 10.066 | 0.025 | 19.803 | 1.523 |
| high-sharing-large | Payload 2 | 1 | 16,641 | 32,768 | 986,827 | 9.316 | 9.901 | 0.024 | 19.241 | 1.671 |
| mixed-transparency | Trimesh 1 | 3 | 1,875 | 3,456 | 559,437 | 0.000 | 3.314 | 0.012 | 3.326 | 1.884 |
| mixed-transparency | Trimesh 2 | 3 | 1,875 | 3,456 | 559,437 | 0.000 | 3.291 | 0.015 | 3.306 | 1.767 |
| mixed-transparency | Payload 1 | 3 | 1,875 | 3,456 | 106,523 | 2.638 | 1.604 | 0.041 | 4.283 | 0.893 |
| mixed-transparency | Payload 2 | 3 | 1,875 | 3,456 | 106,523 | 2.672 | 1.611 | 0.040 | 4.323 | 0.941 |
| representative-large-model | Trimesh 1 | 5 | 83,205 | 163,840 | 26,249,494 | 0.000 | 83.699 | 0.013 | 83.712 | 29.141 |
| representative-large-model | Trimesh 2 | 5 | 83,205 | 163,840 | 26,249,494 | 0.000 | 81.467 | 0.013 | 81.480 | 28.659 |
| representative-large-model | Payload 1 | 5 | 83,205 | 163,840 | 4,932,215 | 42.900 | 48.582 | 0.049 | 91.531 | 8.637 |
| representative-large-model | Payload 2 | 5 | 83,205 | 163,840 | 4,932,215 | 41.136 | 48.691 | 0.053 | 89.880 | 6.725 |

### Renderer and composed-latency results

`Setup` is the separately reported cold GL context/shader metric and is not part
of `Composed latency`.

| Case | Path/run | Prepare | Setup (excluded) | Upload | First draw | Composed latency |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| high-sharing-small | Trimesh 1 | 0.708 | 64.024 | 0.316 | 9.103 | 13.734 |
| high-sharing-small | Trimesh 2 | 0.754 | 63.713 | 0.314 | 9.163 | 13.761 |
| high-sharing-small | Payload 1 | 0.572 | 64.666 | 0.326 | 9.022 | 13.510 |
| high-sharing-small | Payload 2 | 0.547 | 64.565 | 0.319 | 9.128 | 13.545 |
| high-sharing-large | Trimesh 1 | 4.075 | 25.302 | 0.816 | 6.991 | 39.758 |
| high-sharing-large | Trimesh 2 | 4.493 | 30.955 | 0.790 | 6.651 | 38.325 |
| high-sharing-large | Payload 1 | 3.073 | 26.256 | 1.048 | 6.605 | 32.052 |
| high-sharing-large | Payload 2 | 3.043 | 28.561 | 1.112 | 6.665 | 31.732 |
| mixed-transparency | Trimesh 1 | 0.994 | 26.389 | 0.264 | 6.106 | 12.574 |
| mixed-transparency | Trimesh 2 | 0.962 | 25.935 | 0.270 | 6.625 | 12.930 |
| mixed-transparency | Payload 1 | 0.675 | 26.361 | 0.282 | 6.611 | 12.744 |
| mixed-transparency | Payload 2 | 0.662 | 25.773 | 0.291 | 6.511 | 12.728 |
| representative-large-model | Trimesh 1 | 21.720 | 25.258 | 3.724 | 7.175 | 145.472 |
| representative-large-model | Trimesh 2 | 21.565 | 25.259 | 3.735 | 7.078 | 142.517 |
| representative-large-model | Payload 1 | 15.065 | 26.148 | 3.898 | 7.231 | 126.362 |
| representative-large-model | Payload 2 | 15.231 | 25.402 | 3.924 | 7.059 | 122.819 |

### Memory retention and export observations

For the representative list case, the Trimesh counterfactual recorded about
58.5 MB main-process and 23.0 MB publication-child Python peaks; payload runs
recorded about 27.4 MB and 26.8 MB respectively. These are separate concurrent
process observations, not values to sum. List/debug cases retain no export
source. For the exportable large single-mesh case, retained-source RSS deltas
ranged from 12.0–15.7 MB for the counterfactual and 16.4–16.5 MB for payload
runs; allocator noise makes these deltas approximate. Correlated STL export
completion took 8.2–9.0 ms across those four runs.

### Human visual validation evidence

Task 7.3 was completed through a user-confirmed manual before/after GUI
comparison and originally recorded in commit `f2cf097` on 2026-09-11 at 18:14
MDT. This section restores that contemporaneous result after it was removed by a
later benchmark-evidence rewrite. Automated renderer tests and benchmark output
are not being substituted for the human result.

The local `.scadview/debug_info.json` runtime snapshot was captured separately
at `2026-09-13T03:25:25.167385+00:00`. It corroborates the detailed environment
used for this evidence but is not itself treated as proof of visual parity:

- macOS 26.6.2 / Darwin 25.6.0 on an Apple M3 Max, with the Python process
  reporting `x86_64` architecture;
- CPython 3.11.13 built with Clang 20.1.4;
- wxPython 4.2.5 using wxWidgets 3.2.9 and the macOS Cocoa backend;
- ModernGL 5.12.0 with Apple OpenGL 4.1, renderer `Apple M3 Max`, and version
  `4.1 Metal - 90.5`;
- NumPy 2.3.4 and Trimesh 4.9.0.

The user-confirmed comparison recorded visual parity for every required scene:

| Scene | Manual checks | Recorded result |
| --- | --- | --- |
| Startup | Geometry, default color, framing, axes, labels, and gnomon | Pass — parity confirmed |
| Loading | Placeholder geometry, background color, axes, and transition | Pass — parity confirmed |
| Base axes | Visibility, labels, and scale while framing small and large meshes | Pass — parity confirmed |
| Opaque single mesh | Flat shading, color, framing, and depth behavior | Pass — parity confirmed |
| Transparent multi-mesh | Per-mesh colors, global triangle ordering, and depth/blend behavior | Pass — parity confirmed |
| Feature-debug list | Ordering, per-mesh colors, background, and export state | Pass — parity confirmed |
| Incremental generator | Intermediate replacement and final completion behavior | Pass — parity confirmed |
| Edges on/off | Every triangle boundary, including shared vertices | Pass — parity confirmed |
| Framing | Each supported view and framing after resize/orbit operations | Pass — parity confirmed |

No required checklist item lacks evidence in the user-confirmed record, so task
7.3 remains checked. The result establishes parity on the recorded macOS/OpenGL
configuration; it does not claim validation on untested platforms.

### Interpretation and indexed-renderer gate

The payload final envelope is about 81% smaller for all four deterministic cases.
For the representative case, that reduces measured child-to-main transfer from
about 29 ms to about 7–9 ms and renderer preparation from about 22 ms to 15 ms.
However, current payload publication spends about 41–43 ms converting and 49 ms in
the two source-signature passes. Publication work, not renderer upload, is the
largest measured stage. Upload plus first draw remains about 10–11 ms.

These same-version observations continue to support deferring a fully indexed
renderer: expansion/upload is not the dominant current cost, and shader work
would add portability and visual-regression risk. The user-confirmed visual
checklist found no parity regression on the recorded Apple OpenGL platform. This
gate is a conservative diagnostic decision, not proof that the OpenSpec's
chronological baseline requirement was met. A future performance claim requiring
before/after acceptance must establish a valid baseline before changing
production behavior.
