## Context

The loader process currently imports the user module and calls `create_mesh()`
without arguments. The main process communicates with that loader only through
typed multiprocessing queues. The controller already owns feature reload state,
and the wx UI rebuilds feature controls from observable state. See
`proposal.md` for the motivation and user-facing scope.

## Goals / Non-Goals

**Goals:**

- Keep module import, signature inspection, and mesh execution inside the
  isolated loader process.
- Represent parameter metadata and values with small, picklable data models.
- Reuse the existing load/reload lifecycle and dynamic feature-control pattern.
- Make parameter edits explicit and valid before starting a rebuild.
- Ensure only the newest load request can update visible application state.
- Preserve the existing `create_mesh` return-value contract and existing modules
  that take no parameters.

**Non-Goals:**

- Supporting required parameters, arbitrary Python defaults, containers, enums,
  or custom UI widgets in the first version.
- Inferring numeric slider ranges from a function signature.
- Executing user modules in the main process for inspection.
- Changing CLI export behavior or the accepted mesh return types.

## Decisions

### Discover metadata in the loader process

`ModuleLoader` will resolve `create_mesh`, inspect its signature, and expose a
serializable description of supported defaulted scalar parameters. Invocation
will use keyword arguments assembled from the command's parameter-value map.
This avoids importing user code twice and preserves the current process
isolation boundary.

Only ordinary named parameters and keyword-only parameters with defaults are
eligible. Positional-only parameters, required parameters, and variadic
parameters are not exposed as controls; existing invocation errors remain load
errors. Parameters with defaults outside the scalar set are not exposed as
controls and retain their Python defaults.

### Use explicit scalar descriptors

The process protocol will carry parameter descriptors containing a name, scalar
type tag, and default value, plus a map of current values. Only exact built-in
`bool`, `int`, `float`, and `str` defaults are serialized; `bool` is classified
before `int`, and `None`, mutable values, enums, paths, NumPy scalars, and custom
subclasses are unsupported. Type annotations may document the parameter, but
runtime eligibility and conversion are determined by the supported default value
so existing unannotated modules continue to work.

This is preferable to sending `inspect.Signature` or annotation objects, which
may not be picklable or meaningful in the main process.

### Commit UI edits on Enter or focus loss

Numeric and string controls will allow intermediate text while the user edits,
but will convert and validate only when the edit is committed by Enter or focus
loss. Boolean controls can commit immediately. Invalid input stays in the
control long enough to show an error and does not enqueue a load. The last
accepted typed value remains the controller's state.

This avoids rebuilding on every keystroke and avoids treating incomplete text
such as `-` or `1.` as a failed model load.

Boolean parameters use checkboxes and emit actual `bool` values directly; they
are not parsed from arbitrary strings such as `"false"`.

### Return metadata with load results

The first result for a load will carry the discovered parameter descriptors. The
controller will publish them through a parameter observable and the UI will
rebuild a dedicated parameter section alongside feature controls. If module
execution fails after signature discovery, the metadata remains available with
the error result so the user can correct parameter input without losing the
controls. Syntax or import failures have no metadata and retain the normal error
path.

### Keep parameter state in the controller

The controller will own the accepted parameter values for the active module.
Initial values come from discovered defaults. Parameter changes, feature changes,
debug changes, and reloads of the same module reuse the current values. Loading
a different module, determined by comparing normalized absolute paths, clears the
old values and initializes from the new metadata.
When a source edit changes the signature, values are retained only when the
parameter name and supported type still match; new parameters use defaults and
removed or incompatible parameters are discarded.

### Reset values from current parameter metadata

The controller will expose a reset operation that derives values from the
currently published parameter descriptors rather than re-importing the module.
It will replace accepted values with each descriptor's default and enqueue one
reload only when the value map changes. The UI will keep the Reset Parameters
control with the parameter section and start polling only when the controller
actually queues that reload.

### Add request generations to load protocol

Each controller-issued load gets a monotonically increasing request generation.
The generation is copied into commands and results. The controller ignores
results older than its newest requested generation before updating mesh, status,
features, or parameter metadata. `Controller.check_load_queue()` returns a
no-op result for a discarded stale result, and `MainFrame` only updates the
renderer, error display, controls, or polling timer for the current generation.
Queue insertion also compares generations when the bounded result queue is full:
an older result may be discarded for a newer one, but an older worker must never
evict a newer queued result. This closes a race already possible when rapid
parameter edits overlap cooperative loader cancellation.

Alternatives such as debouncing all requests or relying on queue ordering do not
provide correctness for long-running `create_mesh` calls and are therefore not
used as the primary protection.

### Update documentation and tests with the behavior

The implementation will update the `create_mesh` and UI documentation to explain
the supported parameter subset and commit behavior. Tests will target signature
extraction and invocation, command/result serialization, controller state and
generation filtering, and UI event routing through stable seams. Full visual
verification of the wx layout remains a manual check.

## Risks / Trade-offs

- [Long-running builds remain cooperative] -> Request generations prevent stale
  results from being shown, but cannot interrupt Python execution immediately.
- [Some valid Python defaults are not controllable] -> Keep the initial scalar
  contract explicit and document unsupported values rather than serializing
  arbitrary objects.
- [Metadata arrives only after module import and initial execution starts] ->
  Publish metadata on the first available result and preserve it on execution
  errors; controls do not need to appear before the initial build completes.
- [Source edits can change parameter types or names] -> Reconcile state by name
  and scalar type, falling back to the new default when reconciliation is not
  safe. Identify the active module by its normalized absolute path.
- [wx controls are difficult to exercise in headless CI] -> Keep conversion and
  controller update logic in testable non-GUI seams and limit UI tests to mocked
  event routing.

## Migration Plan

No data migration or dependency migration is required. Existing zero-argument
modules continue to load unchanged. Update the user and UI documentation with
the new optional behavior. If the feature is reverted, remove parameter metadata
and value fields from the protocol and return to zero-argument invocation;
existing modules remain compatible in either direction.
