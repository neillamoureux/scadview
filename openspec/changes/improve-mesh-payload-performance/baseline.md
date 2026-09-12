## Trimesh baseline

Command:

```console
uv run python -m tools.mesh_transfer_benchmark --output baseline.json
```

Environment: macOS 26.6.2 x86_64, CPython 3.11.13, NumPy 2.3.4, Trimesh
4.9.0, and ModernGL 5.12.0. The benchmark used a standalone OpenGL context.
Peak memory is Python allocation peak reported by `tracemalloc`; it does not
include driver or GPU allocations.

Two consecutive complete runs on this environment produced the following
results. Timings are milliseconds; pickle size and peak memory are bytes.

| Case | Run | Meshes | Vertices | Faces | Pickle | Convert | Encode | Decode | Queue | Peak | Prepare | Upload | First frame |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| high-sharing-small | 1 | 1 | 1,089 | 2,048 | 76,183 | 1.270 | 0.258 | 0.339 | 1.130 | 1,708,758 | 1.147 | 8.475 | 67.486 |
| high-sharing-small | 2 | 1 | 1,089 | 2,048 | 76,183 | 1.311 | 0.265 | 0.339 | 1.269 | 1,705,092 | 1.231 | 8.579 | 7.910 |
| high-sharing-large | 1 | 1 | 16,641 | 32,768 | 1,186,720 | 1.205 | 0.551 | 0.115 | 1.674 | 20,558,854 | 6.198 | 128.711 | 5.309 |
| high-sharing-large | 2 | 1 | 16,641 | 32,768 | 1,186,720 | 0.950 | 0.533 | 0.106 | 2.019 | 20,567,161 | 6.184 | 125.017 | 5.997 |
| mixed-transparency | 1 | 3 | 1,875 | 3,456 | 129,611 | 0.727 | 0.180 | 0.122 | 0.719 | 1,332,908 | 1.294 | 13.020 | 5.176 |
| mixed-transparency | 2 | 3 | 1,875 | 3,456 | 129,611 | 0.895 | 0.252 | 0.146 | 0.866 | 1,331,104 | 1.467 | 12.601 | 5.540 |
| representative-large-model | 1 | 5 | 83,205 | 163,840 | 5,931,284 | 3.370 | 3.138 | 1.096 | 6.193 | 50,168,210 | 26.997 | 644.396 | 5.842 |
| representative-large-model | 2 | 5 | 83,205 | 163,840 | 5,931,284 | 3.622 | 3.072 | 1.094 | 5.839 | 50,165,804 | 29.374 | 640.914 | 5.643 |

`Convert` is deterministic construction of the source `Trimesh` workload.
`Prepare` records the existing triangle, face-normal, color, and edge-marker
array preparation. `Upload` and `First frame` use the existing VAO helper and
the first VAO draw, each synchronized with `Context.finish()`. The first
small-case draw includes cold-context overhead, so timing values are evidence,
not CI thresholds.

## Compact payload comparison

Command, run 1:

```console
uv run --no-sync python -m tools.mesh_transfer_benchmark --path payload --output compact-run1.json
```

Command, run 2:

```console
uv run --no-sync python -m tools.mesh_transfer_benchmark --path payload --output compact-run2.json
```

Both runs used the same environment recorded above, the same deterministic
cases, standalone ModernGL, and Python `tracemalloc` peak allocation. The
compact path serializes `MeshPayload` values and expands them into the same
triangle-corner GPU inputs used by the renderer.

| Case | Run | Pickle | Payload conversion | Encode | Decode | Queue | Peak | Prepare | Upload | First frame |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| high-sharing-small | 1 | 62,675 | 1.681 | 0.202 | 0.276 | 0.960 | 1,190,172 | 0.631 | 0.327 | 7.753 |
| high-sharing-small | 2 | 62,675 | 1.730 | 0.202 | 0.276 | 0.960 | 1,192,975 | 0.636 | 0.320 | 8.189 |
| high-sharing-large | 1 | 986,606 | 7.967 | 0.282 | 0.085 | 1.279 | 12,353,728 | 3.054 | 0.918 | 5.502 |
| high-sharing-large | 2 | 986,606 | 7.816 | 0.282 | 0.085 | 1.279 | 12,352,130 | 2.658 | 1.012 | 5.545 |
| mixed-transparency | 1 | 106,299 | 2.099 | 0.169 | 0.110 | 0.600 | 1,302,278 | 0.538 | 0.294 | 5.050 |
| mixed-transparency | 2 | 106,299 | 1.935 | 0.169 | 0.110 | 0.600 | 1,302,554 | 0.470 | 0.270 | 5.718 |
| representative-large-model | 1 | 4,931,991 | 40.618 | 1.105 | 0.942 | 5.030 | 56,909,007 | 14.837 | 3.702 | 5.802 |
| representative-large-model | 2 | 4,931,991 | 37.562 | 1.105 | 0.942 | 5.030 | 56,901,319 | 14.089 | 3.411 | 5.310 |

The compact pickle is 17.7%, 16.9%, 18.0%, and 16.9% smaller than the
corresponding recorded Trimesh baseline for the four cases. Payload conversion
is the new dominant measured cost for the large representative case; GPU
upload and first-frame measurements do not indicate that a fully indexed
renderer is currently the material bottleneck. These timings are evidence, not
CI thresholds.

### Post-create-mesh time to first frame

The benchmark also emits `post_create_mesh_to_first_frame_ms`, which covers the
work after deterministic mesh creation completes: payload conversion when
applicable, serialization, queue round trip, renderer preparation, GL buffer
creation, and the first draw. The original renderer did not emit this aggregate
metric, so the historical value below is reconstructed by summing the recorded
phase timings; it is an estimate rather than a new measurement.

| Case | Historical Trimesh renderer | Compact payload renderer | Reduction |
| --- | ---: | ---: | ---: |
| high-sharing-small, run 1 | 78.835 ms (estimated) | 11.830 ms | 85.0% |
| high-sharing-small, run 2 | 19.593 ms (estimated) | 12.313 ms | 37.2% |
| high-sharing-large, run 1 | 142.558 ms (estimated) | 19.087 ms | 86.6% |
| high-sharing-large, run 2 | 139.856 ms (estimated) | 18.677 ms | 86.6% |
| mixed-transparency, run 1 | 20.511 ms (estimated) | 8.860 ms | 56.8% |
| mixed-transparency, run 2 | 20.872 ms (estimated) | 9.272 ms | 55.6% |
| representative-large-model, run 1 | 687.662 ms (estimated) | 72.036 ms | 89.5% |
| representative-large-model, run 2 | 685.936 ms (estimated) | 67.449 ms | 90.2% |

The representative large model therefore reduced the estimated UI-blocking
interval by approximately 90%. The reduction is primarily in synchronous CPU
render-buffer preparation and GL buffer creation, not pickle size alone. The
historical and compact rows combine the transport and renderer changes, so they
should not be interpreted as an isolated serialization experiment.

## Human visual validation checklist

Not run in this environment: no supported SCADview GUI session was available.
On a supported GUI/OpenGL platform, compare the same startup and loaded scenes
before and after the change, recording OS, Python, GPU, driver, and OpenGL
version:

- startup mesh: geometry, default color, framing, axes, labels, and gnomon;
- loading placeholder: geometry, background color, axes, and transition;
- base axes: visibility, scale while framing small and large meshes, and labels;
- opaque single mesh: flat shading, color, framing, and depth behavior;
- transparent multi-mesh list: multiple mesh colors, global triangle ordering,
  and depth/blend behavior;
- feature-debug list: ordering, per-mesh colors, background, and export state;
- incremental generator results: replacement and final completion behavior;
- edge display on and off: every triangle boundary, including shared vertices;
- framing from each supported view direction and after resize/orbit operations.

Until this checklist is completed by a human, visual parity remains unverified.

## Indexed-renderer gate

Based on the compact benchmark, fully indexed shader rendering remains deferred:
serialized transfer improved materially, while upload and first-frame timings are
small relative to payload conversion and retained temporary allocation. The
human visual checklist above is still outstanding, so this is a provisional
gate decision and does not authorize an indexed-renderer redesign or a separate
change.
