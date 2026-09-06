## 1. Parameter discovery and invocation

- [ ] 1.1 Add serializable parameter descriptor types and module-loader method stubs for signature discovery and keyword invocation; verify the new interfaces are importable without changing zero-argument behavior
- [ ] 1.2 Add failing module-loader tests for supported defaults, signature order, positional-only and variadic parameters, unsupported defaults, required parameters, and invocation with keyword values; verify the tests fail for the missing discovery/invocation behavior
- [ ] 1.3 Implement signature discovery and typed keyword invocation for supported `bool`, `int`, `float`, and `str` defaults; verify `uv run pytest tests/test_module_loader.py` passes

## 2. Loader process protocol

- [ ] 2.1 Add command/result fields and loader-worker plumbing stubs for parameter values, parameter metadata, and request generations; verify existing command/result construction remains compatible
- [ ] 2.2 Add failing mesh-loader tests for parameter propagation, metadata delivery on successful and post-discovery failed loads, generation values, and bounded-queue handling that preserves newer results; verify the tests fail for the missing protocol behavior
- [ ] 2.3 Implement process-boundary parameter propagation, metadata reporting, and generation-aware queue insertion that never evicts a newer queued result while preserving feature capture and accepted mesh return types; verify `uv run pytest tests/test_mesh_loader_process.py` passes

## 3. Controller state and stale-result handling

- [ ] 3.1 Add controller parameter-state, metadata-observable, and request-generation method stubs; verify the controller still initializes and closes with existing queue seams
- [ ] 3.2 Add failing controller tests for defaults, valid parameter updates, persistence across feature/debug reloads, normalized-path identity, signature reconciliation, no-op stale success/error/final-result rejection, and UI-facing current-generation state; verify the tests fail for the missing state behavior
- [ ] 3.3 Implement controller-owned parameter state, reload commands, metadata publication, validation boundaries, and authoritative generation filtering before any state mutation; verify `uv run pytest tests/test_controller.py` passes

## 4. UI controls and documentation

- [ ] 4.1 Add parameter-control construction and value-conversion stubs alongside the existing feature-control helpers; verify mocked control creation has the expected parameter labels and initial values
- [ ] 4.2 Add failing UI-focused tests for numeric/string commit validation, boolean updates using actual `bool` values, invalid-input retention, reload routing, control replacement, post-discovery error metadata, and ignoring stale results without stopping the current timer; verify the tests fail for the missing UI behavior
- [ ] 4.3 Implement the Parameters section and commit event handling, then document the supported signature and UI behavior in `docs/create_mesh.md`, `docs/user_interface.md`, and `docs/cli_export.md`; verify the targeted UI tests and documentation checks pass

## 5. Integration validation

- [ ] 5.1 Run the focused loader, process, controller, and UI tests together and verify the full parameterized-module flow from control edit to rendered mesh
- [ ] 5.2 Run `uv run ruff check`, `uv run ty check`, and the repository preflight task; resolve any regressions without changing the documented scope
- [ ] 5.3 Manually load a module defining `create_mesh(width: float = 2.5)`, change the control, toggle a feature if present, and confirm the newest geometry remains visible after rapid edits
