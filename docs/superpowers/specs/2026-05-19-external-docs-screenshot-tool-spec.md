# External Docs Screenshot Tool Specification

## Purpose

Move the docs screenshot automation out of the `scadview` package while keeping
the actual application behavior under test. The screenshot generator is a
repository-local documentation/build tool, not part of the installed SCADview
runtime API.

The tool may import `scadview` and drive the real wx application components, but
`scadview` must not import the tool, its manifest models, or docs-specific
workflow code.

## Background

Current screenshot automation crosses an architectural boundary:

- `src/scadview/docs_screenshots.py` contains docs manifest parsing, validation,
  CLI orchestration, and capture backend abstractions inside the runtime package.
- `src/scadview/ui/wx/docs_capture.py` wires `Controller`, `RendererFactory`,
  `GlWidgetAdapter`, and `MainFrame` from inside the wx UI package.
- `MainFrame` exposes docs-specific methods and type references such as
  `load_docs_screenshot_module`, `poll_docs_screenshot_load`, and
  `apply_docs_screenshot_state`.

The desired dependency direction is:

```text
repository docs tool -> scadview package
```

The forbidden dependency direction is:

```text
scadview package -> repository docs tool
```

## Goals

- Keep docs screenshot manifest parsing, validation, CLI entrypoint, and capture
  orchestration outside `src/scadview`.
- Preserve clear user-facing workflows for maintainers:
  `mise run docs_check_screenshots_manifest` for CI-safe validation and
  `mise run docs_generate_screenshots` for local generation.
- Preserve the ability to validate the manifest in CI without importing wx.
- Preserve the ability to generate all screenshots locally by default, with an
  option to pass selected screenshot names.
- Keep GL access inside the render layer. wx may manage the native GL context,
  but it must not import or call ModernGL directly.
- Replace docs-specific `MainFrame` methods with neutral automation methods that
  are meaningful for any caller driving the app programmatically.
- Keep the change small and reviewable. Avoid unrelated file moves, UI redesign,
  or renderer refactoring.

## Non-Goals

- Do not add a public user-facing screenshot API to `scadview`.
- Do not change the documented `create_mesh` user module contract.
- Do not change the visual design of the UI.
- Do not add new runtime dependencies.
- Do not make GUI screenshot generation mandatory in CI.
- Do not commit regenerated PNGs unless the user explicitly asks for that.

## Target File Layout

### New Or Moved Tool Code

Create a repository-local tool outside the package in a top-level `tools/`
directory:

```text
tools/__init__.py
tools/docs_screenshots.py
```

This location is required. The screenshot generator is maintained repository
automation, not installed application code. Keeping it in `tools/` makes the
dependency direction explicit:

```text
tools/docs_screenshots.py -> scadview
```

Do not place this tool under `src/scadview`, and do not introduce an alternate
`scripts/` directory for it unless the project later adopts that convention for
all developer tooling.

`tools/` must be an importable package so tests can use normal imports such as:

```python
from tools.docs_screenshots import validate_manifest
```

Because SCADview uses a `src/` package layout, this top-level package is
repo-local tooling and must not be added to the installed `scadview` runtime
package.

This module owns:

- `ScreenshotManifestError`
- `ScreenshotEntry`
- `ScreenshotManifest`
- Manifest parsing and validation.
- Markdown image reference scanning.
- CLI parsing.
- Screenshot generation orchestration.
- wx capture backend or backend protocol used only by the tool.

The tool may import these SCADview runtime components:

- `scadview.controller.Controller`
- `scadview.load_status.LoadStatus`
- `scadview.render.camera.CameraPerspective`
- `scadview.render.gl_widget_adapter.GlWidgetAdapter`
- `scadview.render.renderer.RendererFactory`
- `scadview.ui.wx.main_frame.MainFrame`

The tool must not be imported from `src/scadview`.

### Runtime Package Code

Keep reusable, product-shaped behavior in the runtime package:

```text
src/scadview/ui/wx/main_frame.py
src/scadview/ui/wx/gl_widget.py
src/scadview/render/gl_widget_adapter.py
src/scadview/render/renderer.py
```

`MainFrame` may expose neutral automation hooks:

- `load_module(module_path: Path) -> None`
- `poll_load_status() -> LoadStatus`
- `apply_view_state(view_state: ViewState) -> None`
- `capture_client_bitmap() -> wx.Bitmap`

The exact names may differ, but they must not mention docs, screenshots, or
manifest concepts.

If `ViewState` is needed inside the runtime package, define it as a small,
neutral dataclass in an appropriate UI module, for example:

```text
src/scadview/ui/view_state.py
```

The runtime `ViewState` must describe UI/render state only:

- `view`
- `camera`
- `grid`
- `axes`
- `edges`
- `gnomon`

It must not contain docs paths, manifest names, output paths, or module paths.

### Tasks

Update:

```text
tasks.py
mise.toml
```

The external tool should default to validation-only behavior. Screenshot capture
should require an explicit `--generate` flag. The `mise run
docs_check_screenshots_manifest` command should remain validation-only and
CI-safe. It should invoke the external tool, not
`python -m scadview.docs_screenshots`.

Example target behavior:

```text
mise run docs_check_screenshots_manifest
```

runs:

```text
python tools/docs_screenshots.py --manifest docs/screenshots.toml
```

Generation should use a separate task that generates all screenshots by default:

```text
mise run docs_generate_screenshots
```

Selected screenshots should be passed as positional arguments:

```text
mise run docs_generate_screenshots -- grid sphere
```

## Required Behavior

### Manifest Validation

The external tool must preserve current validation behavior:

- Manifest must contain a top-level `screenshots` list.
- Each screenshot entry must define exactly the required fields currently used
  by `docs/screenshots.toml`.
- Names must be unique.
- Selected names must exist.
- Output paths must be relative, stay inside `docs/`, use `.png`, and be
  referenced from `README.md` or `docs/**/*.md`.
- Module paths must be relative, stay inside the repository, and point to an
  existing file.
- Supported views remain `frame`, `xyz`, `x`, `y`, and `z`.
- Supported cameras remain `perspective` and `orthogonal`.
- `window_size` must contain two positive integer values.
- Validation must not import wx or construct any application objects.
- Validation is the default mode when neither `--check` nor `--generate` is
  passed.

### Screenshot Generation

Generation must:

- Validate the manifest before capturing.
- Run only when `--generate` is passed.
- Create or reuse a `wx.App`.
- Compose runtime dependencies outside `src/scadview/ui/wx`:
  `RendererFactory`, `GlWidgetAdapter`, `Controller`, and `MainFrame`.
- Load the selected module through a neutral `MainFrame` method.
- Wait for `LoadStatus.COMPLETE`.
- Fail with a clear exception on `LoadStatus.ERROR`.
- Fail with a timeout if loading does not complete.
- Apply manifest state by translating `ScreenshotEntry` to runtime `ViewState`
  in the external tool.
- Capture the client area including the GL canvas and UI buttons.
- Save PNG output, creating parent directories as needed.
- Close/destroy wx resources and close the controller in a `finally` path.

### Runtime Package Boundaries

`src/scadview` must not contain:

- `docs_screenshots.py`
- `ui/wx/docs_capture.py`
- `ScreenshotEntry`
- `ScreenshotManifest`
- `ScreenshotCaptureRequest`
- `ScreenshotCaptureBackend`
- Any import from `tools.docs_screenshots` or equivalent external tool module.
- Any `MainFrame` method name containing `docs_screenshot`.

`src/scadview/ui/wx/gl_widget.py` must not import `moderngl`.

`src/scadview/render/renderer.py` remains the owner of ModernGL framebuffer
readback.

## Testing Requirements

The developer should update tests first, then implementation.

Place tests for the external tool under:

```text
tests/tools/test_docs_screenshots.py
```

If the test file becomes difficult to scan, split it by behavior:

```text
tests/tools/test_docs_screenshots_manifest.py
tests/tools/test_docs_screenshots_generation.py
```

Tests should import the tool through the `tools` package, not by loading the file
with `importlib.util`.

### Manifest Tests

Move or update current docs screenshot tests so they import the external tool
module rather than `scadview.docs_screenshots`.

Keep coverage for:

- Repository manifest has expected screenshot entries.
- Repository manifest validates without importing wx.
- Valid manifest parsing.
- Selected screenshot subsets.
- Duplicate names.
- Unknown selected names.
- Outputs escaping docs.
- Absolute paths.
- Missing modules.
- Modules escaping the repo.
- Unsupported views.
- Unsupported cameras.
- Invalid window sizes.
- Non-PNG outputs.
- Outputs not referenced from docs markdown.
- Markdown outside `README.md` and `docs/` is ignored.

### Generation Boundary Tests

Keep tests that prove generation orchestration:

- Validates before capture.
- Builds capture requests with resolved module and output paths.
- Delegates to an injected/fake capture backend.
- Does not import wx when running in `--check` mode.

These tests should not require a real GUI.

### Runtime Boundary Tests

Add or adjust focused tests for runtime primitives where practical:

- Renderer pixel readback remains in `Renderer.capture_pixels`.
- `GlWidgetAdapter.capture_pixels` delegates through the renderer after render.
- Any new neutral `ViewState` type maps cleanly from external manifest state.

Do not add brittle tests for platform-specific wx screenshot pixels unless the
project has a reliable GUI test environment.

## Validation Commands

Run the smallest relevant checks first:

```bash
uv run --no-sync pytest tests/tools/test_docs_screenshots.py tests/render/test_renderer.py -q
```

Run lint and format checks on changed files:

```bash
uv run --no-sync ruff check tools/docs_screenshots.py tests/tools/test_docs_screenshots.py src/scadview/ui/wx/main_frame.py src/scadview/ui/wx/gl_widget.py src/scadview/render/gl_widget_adapter.py src/scadview/render/renderer.py tasks.py
uv run --no-sync ruff format --check tools/docs_screenshots.py tests/tools/test_docs_screenshots.py src/scadview/ui/wx/main_frame.py src/scadview/ui/wx/gl_widget.py src/scadview/render/gl_widget_adapter.py src/scadview/render/renderer.py tasks.py
```

Run type checking in the project’s expected mode:

```bash
uv run --no-sync ty check --exclude src/scadview/ui/wx --force-exclude src/scadview tasks.py
```

When practical, run the full preflight:

```bash
mise preflight
```

## Manual Verification

After implementation, a human should generate screenshots locally and inspect
the resulting PNGs:

```bash
mise run docs_generate_screenshots
```

If the final command syntax differs, document it in the PR summary and update
this spec or the relevant docs/task help.

Manual verification must confirm:

- PNGs are generated.
- The GL content is visible, not black.
- The UI buttons are included.
- Window/client sizing is acceptable on the developer’s platform.
- Existing docs references still point to generated files.

## Acceptance Criteria

- `src/scadview` no longer contains docs screenshot tool orchestration.
- The external tool imports and drives SCADview rather than SCADview importing
  the external tool.
- No docs-specific models or method names remain in `MainFrame`.
- `mise run docs_check_screenshots_manifest` validates the manifest without
  importing wx.
- `mise run docs_generate_screenshots` generates all screenshots by default and
  accepts optional screenshot names.
- Local generation still captures the app client area including GL and buttons.
- Existing targeted tests pass.
- Lint, format, and type checks pass for changed files.
- Generated PNGs are left unstaged unless explicitly requested.

## Recommended Commit Shape

Use small commits so review can separate architecture from behavior:

1. `test: cover external docs screenshot tool boundary`
2. `refactor: move docs screenshot tooling outside package`
3. `refactor: make screenshot frame hooks neutral`
4. `chore: update docs screenshot task entrypoint`
