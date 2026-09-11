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
