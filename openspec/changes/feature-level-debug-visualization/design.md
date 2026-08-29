## Context

Feature meshes currently act as boolean-operation proxies and are reduced to native meshes before crossing the loader boundary. The existing renderer already supports an ordered list of meshes as translucent debug output, but that list has no feature identity. Mesh generation occurs in a worker process, so the visualization mode must travel with the load command.

## Goals / Non-Goals

**Goals:**

- Capture source geometry before boolean composition.
- Preserve feature names, enabled state, and registration order internally.
- Reuse the existing list-debug rendering path.
- Keep the public `feature(...)` API and `create_mesh` return contract unchanged.
- Preserve progressive loading semantics.

**Non-Goals:**

- Per-feature debug toggles or labels.
- Showing disabled features.
- Inferring source ownership from final boolean meshes.
- Overlaying source geometry on the final mesh in the first version.

## Decisions

The feature context will store an internal frozen source-record containing the
feature name, native-mesh reference, and resolved enabled state. Registration will
append a record on every `feature(...)` call; the decorator path already converges
on this registration path. The registration log is cleared before each module
execution, remains available through emission of that execution's final
`LoadResult`, and is then discarded. Capturing references at registration avoids
unreliable identity inference after boolean operations while avoiding copies when
debug visualization is off. Keeping the record separate from `FeatureMesh`
prevents boolean behavior and visualization concerns from being coupled.

The controller and loader command will carry a separate `debug_features` boolean.
The controller owns this state, initializes it to `False`, retains it across
reloads and module-path changes, and triggers a reload when the user changes it.
It is not a `FeatureState` and feature discovery must not reset it. The UI will
place one Debug features checkbox in the Features section outside the scrolling
per-feature checkbox list; the control uses controller state and remains separate
from feature enabled controls. The section may remain hidden when no features are
discovered, consistent with the existing feature-controls behavior.

The worker will run the module normally and snapshot the ordered registered
sources at each yield. When debug mode is active and a snapshot contains enabled
sources, it returns those sources as the debug mesh list for that yield. If the
snapshot contains no enabled sources, it retains the normal yielded result. The
same selection is used for the final completion result so it cannot lose captured
sources during module-execution cleanup.

Native `Manifold` sources will be converted to `Trimesh` at the loader boundary.
The existing list-debug color, alpha, renderer, status, and export-disable
behavior will remain responsible for presentation and export eligibility. No
renderer model change is required for the first version.

Documentation will extend the existing `examples/features.py` rather than add a
second feature-debug script. Its `cable_cutout` feature is already a named
subtractive cylinder used as a tool volume, so the example will identify that
role and the rendered `docs/examples.md` inclusion will add a concise walkthrough:
load the example, enable Debug features, observe the tool volume, and distinguish
the global visualization state from the `cable_cutout` enabled state. The existing
example screenshot may remain a normal feature-controls image; the behavior is
explained in text rather than requiring a new UI-state screenshot.

The debug toggle belongs near the feature checkboxes because it changes their visualization, but it is not represented as a `FeatureState`. This preserves the distinction between model inclusion and visualization mode.

## Risks / Trade-offs

- [Source geometry may be large] -> Capture references during module execution and convert only the selected debug output at the loader boundary; accept the additional debug-mode cost.
- [Generator state can be cleared before its completion result] -> Retain the
  source-registration log until after the final load result is selected and emitted.
- [Repeated registrations can produce many debug meshes] -> Preserve them deliberately for semantic correctness and rely on the existing debug renderer behavior.
- [Debug source meshes are not final material] -> Document the source/tool-volume meaning and keep debug output ineligible for export.
- [A Python example cannot enable a UI-only mode] -> Pair the source example with
  explicit rendered-documentation steps instead of adding a public API or implying
  that the script itself turns on Debug features.
- [Feature debug mode changes the displayed result] -> Make it opt-in and fall back to the normal mesh when no feature sources are available.
