## Corrected mesh-transfer comparison

Commands, run twice per path:

```console
uv run --no-sync python -m tools.mesh_transfer_benchmark --path trimesh --output trimesh-run<N>.json
uv run --no-sync python -m tools.mesh_transfer_benchmark --path payload --output payload-run<N>.json
```

Both paths use the same deterministic cases from the current harness, in the
same order and environment. The runs were performed on macOS 26.6.2 x86_64
with CPython 3.11.13, NumPy 2.3.4, Trimesh 4.9.0, and ModernGL 5.12.0.

The harness reports `mesh_creation_ms` before the post-creation aggregate.
`post_create_mesh_to_first_frame_ms` starts immediately after mesh creation and
includes only path-specific payload conversion, one real multiprocessing queue
round trip, renderer preparation, GL upload, and the first draw. Standalone
pickle size is an observation outside that aggregate. Export and retained-source
memory are measured separately.

| Case | Meshes | Vertices | Faces | Path/run | Pickle bytes | Payload conversion ms | Queue ms | Prepare ms | Upload ms | First draw ms | Post-create to first frame ms |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| high-sharing-small | 1 | 1,089 | 2,048 | Trimesh 1 | 76,183 | 0.000 | 1.785 | 1.123 | 0.451 | 49.709 | 137.533 |
| high-sharing-small | 1 | 1,089 | 2,048 | Trimesh 2 | 76,183 | 0.000 | 1.693 | 1.162 | 0.316 | 8.484 | 84.703 |
| high-sharing-small | 1 | 1,089 | 2,048 | Payload 1 | 62,675 | 1.667 | 1.556 | 0.573 | 0.325 | 8.946 | 85.780 |
| high-sharing-small | 1 | 1,089 | 2,048 | Payload 2 | 62,675 | 1.663 | 1.521 | 0.506 | 0.294 | 8.897 | 88.209 |
| high-sharing-large | 1 | 16,641 | 32,768 | Trimesh 1 | 1,186,720 | 0.000 | 1.922 | 7.195 | 0.860 | 5.782 | 44.271 |
| high-sharing-large | 1 | 16,641 | 32,768 | Trimesh 2 | 1,186,720 | 0.000 | 2.077 | 7.555 | 0.855 | 5.872 | 45.677 |
| high-sharing-large | 1 | 16,641 | 32,768 | Payload 1 | 986,606 | 7.820 | 1.588 | 2.610 | 0.952 | 6.094 | 49.895 |
| high-sharing-large | 1 | 16,641 | 32,768 | Payload 2 | 986,606 | 7.805 | 1.411 | 2.535 | 1.031 | 6.322 | 48.294 |
| mixed-transparency | 3 | 1,875 | 3,456 | Trimesh 1 | 129,611 | 0.000 | 1.131 | 1.983 | 0.285 | 6.501 | 39.923 |
| mixed-transparency | 3 | 1,875 | 3,456 | Trimesh 2 | 129,611 | 0.000 | 0.950 | 1.704 | 0.284 | 5.901 | 42.902 |
| mixed-transparency | 3 | 1,875 | 3,456 | Payload 1 | 106,299 | 2.152 | 0.833 | 0.533 | 0.272 | 6.090 | 39.607 |
| mixed-transparency | 3 | 1,875 | 3,456 | Payload 2 | 106,299 | 2.205 | 0.823 | 0.521 | 0.288 | 5.774 | 38.392 |
| representative-large-model | 5 | 83,205 | 163,840 | Trimesh 1 | 5,931,284 | 0.000 | 6.414 | 33.545 | 3.763 | 6.766 | 80.012 |
| representative-large-model | 5 | 83,205 | 163,840 | Trimesh 2 | 5,931,284 | 0.000 | 8.016 | 34.363 | 3.868 | 6.621 | 83.650 |
| representative-large-model | 5 | 83,205 | 163,840 | Payload 1 | 4,931,991 | 36.607 | 7.458 | 13.789 | 3.815 | 6.364 | 99.899 |
| representative-large-model | 5 | 83,205 | 163,840 | Payload 2 | 4,931,991 | 39.839 | 7.181 | 14.426 | 4.277 | 6.771 | 100.745 |

Peak Python allocation during each case was also recorded in the JSON report.
The payload path reduced peak allocation for the representative list case from
about 80.2 MB to 51.8 MB. The synthetic grid generator creates two distinct
non-degenerate triangles per cell; the counts above therefore represent valid
geometry rather than a degenerate-face shortcut.

## Retained loader-process memory

For single-mesh cases, a child process starts with no source, receives the final
source over a pipe, retains it, and reports baseline RSS, final RSS, and their
signed delta. This models loader ownership and avoids reporting an absolute
interpreter RSS or retaining an entire list. List cases are explicitly reported
as `list-or-debug-not-retained` and have no retained-source measurement.

| Case | Path/run | Baseline RSS bytes | Final RSS bytes | Signed retained-source delta bytes | Source kind |
| --- | --- | ---: | ---: | ---: | --- |
| high-sharing-small | Trimesh 1 | 83,308,544 | 83,263,488 | -45,056 | single-final-source |
| high-sharing-small | Trimesh 2 | 83,218,432 | 83,136,512 | -81,920 | single-final-source |
| high-sharing-small | Payload 1 | 83,873,792 | 83,468,288 | -405,504 | single-final-source |
| high-sharing-small | Payload 2 | 84,328,448 | 84,508,672 | 180,224 | single-final-source |
| high-sharing-large | Trimesh 1 | 83,333,120 | 94,654,464 | 11,321,344 | single-final-source |
| high-sharing-large | Trimesh 2 | 83,345,408 | 94,756,864 | 11,411,456 | single-final-source |
| high-sharing-large | Payload 1 | 83,128,320 | 99,713,024 | 16,584,704 | single-final-source |
| high-sharing-large | Payload 2 | 83,181,568 | 100,130,816 | 16,949,248 | single-final-source |
| mixed-transparency | All runs | — | — | — | list-or-debug-not-retained |
| representative-large-model | All runs | — | — | — | list-or-debug-not-retained |

RSS samples are process-level observations and may produce small negative deltas
because of allocator and operating-system sampling behavior.

## End-to-end export completion

For each exportable single-mesh case, the harness starts an `ExportWorker` with a
request, exports to a temporary STL file, waits for the correlated terminal
result on the reliable export-result queue, and reports total request-to-
completion time. List cases are not exportable and report no value.

| Case | Trimesh run 1 ms | Trimesh run 2 ms | Payload run 1 ms | Payload run 2 ms |
| --- | ---: | ---: | ---: | ---: |
| high-sharing-small | 1.694 | 1.619 | 1.307 | 1.199 |
| high-sharing-large | 3.325 | 3.435 | 2.551 | 2.689 |
| mixed-transparency | — | — | — | — |
| representative-large-model | — | — | — | — |

## Indexed-renderer gate

The corrected comparison does not justify a fully indexed renderer in this
change. Payload serialization is smaller and list-case peak allocation is lower,
but payload conversion is the dominant new CPU phase for the representative
case. Renderer preparation, upload, and first draw remain small and comparable
between paths; no corrected result identifies renderer expansion or upload as a
material remaining bottleneck. Fully indexed shader work therefore remains
deferred to a separately reviewable change.
