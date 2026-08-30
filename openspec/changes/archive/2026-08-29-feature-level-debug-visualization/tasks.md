## 1. Feature source model and context

- [x] 1.1 Create the internal feature-source record and feature-context capture/accessor lifecycle stubs; verify the new types are importable and existing feature tests still collect
- [x] 1.2 Add failing tests for source capture at registration, duplicate registration order, enabled-state filtering, decorator registration, capture reset between executions, and Manifold sources; verify failures demonstrate missing capture behavior
- [x] 1.3 Implement ordered feature-source capture through both direct and decorator-based feature registration, retaining records until the worker emits its final result; verify the feature context tests pass

## 2. Loader and command pipeline

- [x] 2.1 Add the separate feature-debug flag to load command/worker stubs and define the per-yield debug-source selection seam; verify command construction preserves the flag
- [x] 2.2 Add failing loader tests for ordered feature-debug snapshots on every yielded result, duplicate registrations, disabled-feature omission, unregistered-mesh omission, no-feature fallback, Manifold conversion, final completion output, and normal mode preservation; verify failures demonstrate missing pipeline behavior
- [x] 2.3 Implement feature-debug propagation and source-mesh selection at the loader boundary, replacing the normal result with translucent enabled sources; verify targeted mesh-loader tests pass

## 3. Controller state and UI

- [x] 3.1 Add controller debug-feature state and reload wiring stubs; verify the state defaults to false and is retained across reloads and module-path changes
- [x] 3.2 Add failing controller and UI tests for toggling debug mode independently of feature checkboxes, retaining the state through feature discovery resets, issuing a reload, and placing the control outside the scrolling per-feature list; verify failures identify missing state/action behavior
- [x] 3.3 Implement controller state propagation and add the global Debug features toggle near the feature controls; verify targeted controller/UI tests pass

## 4. Integration and documentation

- [x] 4.1 Add integration coverage for progressive per-yield source-only debug lists, final completion output, unregistered-mesh omission, and normal fallback when no enabled features are registered; verify the relevant test module passes
- [x] 4.2 Add a failing documentation/example check for separate non-debug and Debug features walkthroughs: retain `features.png` for ordinary enabled/disabled feature behavior with Debug features off; use a manually captured `features_debug.png` for source-only `cable_cutout` debug visualization; explain enabled-state independence and unregistered-mesh omission in both walkthrough and `feature(...)` API docs; verify the check fails before the separate sections, image, and commented issue #161 manifest entry exist
- [x] 4.3 Implement the feature example, walkthrough, and feature API documentation, preserving the existing example's screenshot usage and no-public-API contract; add the manually captured `features_debug.png` without enabling automated generation; verify the example documentation and relevant docs checks pass
- [x] 4.4 After the UI and documentation work, run `mise run docs_check_screenshots_manifest`, regenerate and visually verify the non-debug `docs/images/features.png`, manually capture and visually verify `docs/images/features_debug.png`, and retain the `features_debug.png` manifest entry as a commented issue #161 follow-up; verify the manifest check and generation succeed
- [x] 4.5 Temporarily, pending issue #161's automated screenshot-workflow support, manually launch `examples/features.py`, enable Debug features, wait for the reload, capture the screen, and visually verify that the viewport shows translucent enabled feature source geometry in place of the final composed mesh
- [x] 4.6 Run formatting, linting, type checks, and the relevant test suite with the repository's `uv run`/`mise` tooling; verify all required checks pass
