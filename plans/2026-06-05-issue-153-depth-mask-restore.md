# Issue 153 Problem 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make alpha mesh rendering restore `depth_mask` to `True` after each render pass so later draws do not inherit transparent-render state.

**Architecture:** Keep the fix inside `src/scadview/render/trimesh_renderee.py`, where `AlphaRenderee` already owns the alpha-specific ModernGL state. Use a small render-path change that guarantees the depth write state is restored after `_vao.render()`, and cover it with targeted render-layer tests rather than touching the higher-level `Renderer`.

**Tech Stack:** Python, ModernGL, pytest, unittest.mock

---

### Task 1: Add regression coverage for depth-mask restoration

**Files:**
- Modify: `tests/render/test_trimesh_renderee.py`
- Test: `tests/render/test_trimesh_renderee.py`

- [ ] **Step 1: Replace the current alpha render assertion with a failing restoration test**

Current coverage at `tests/render/test_trimesh_renderee.py:432-448` asserts the buggy state (`depth_mask is False`). Replace that expectation and add an exception-path check so the restoration requirement is explicit.

```python
@mock.patch("scadview.render.trimesh_renderee.create_vao")
def test_alpha_renderee_render_restores_depth_mask_after_render(
    create_vao,
    alpha_renderee,
):
    alpha_renderee._resort_verts = True
    alpha_renderee._sort_buffers = mock.MagicMock()
    vao_mock = mock.MagicMock()
    create_vao.return_value = vao_mock
    alpha_renderee._vao = vao_mock

    alpha_renderee.render()

    alpha_renderee._sort_buffers.assert_called_once()
    vao_mock.render.assert_called_once()
    assert alpha_renderee._ctx.enable.call_count >= 2
    assert alpha_renderee._ctx.depth_mask is True


def test_alpha_renderee_render_restores_depth_mask_when_vao_render_fails(
    alpha_renderee,
):
    alpha_renderee._resort_verts = False
    vao_mock = mock.MagicMock()
    vao_mock.render.side_effect = RuntimeError("render failed")
    alpha_renderee._vao = vao_mock

    with pytest.raises(RuntimeError, match="render failed"):
        alpha_renderee.render()

    assert alpha_renderee._ctx.depth_mask is True
```

- [ ] **Step 2: Run the targeted render test file and verify RED**

Run: `uv run pytest tests/render/test_trimesh_renderee.py -v`

Expected: FAIL because `AlphaRenderee.render()` currently leaves `depth_mask` as `False` at [src/scadview/render/trimesh_renderee.py](../src/scadview/render/trimesh_renderee.py:254).

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/render/test_trimesh_renderee.py plans/2026-06-05-issue-153-depth-mask-restore.md
git commit -m "test: add alpha depth mask regression coverage"
```

### Task 2: Restore `depth_mask` in the alpha render path

**Files:**
- Modify: `src/scadview/render/trimesh_renderee.py`
- Test: `tests/render/test_trimesh_renderee.py`

- [ ] **Step 1: Make `AlphaRenderee.render()` restore depth writes**

Update the render function at `src/scadview/render/trimesh_renderee.py:254-262` so `depth_mask` is always reset after the alpha draw completes.

```python
def render(self):
    if self._resort_verts:
        self._sort_buffers()
    self._ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
    self._ctx.enable(moderngl.DEPTH_TEST)
    self._ctx.enable(moderngl.BLEND)
    # ModernGL exposes depth_mask at runtime, but its stubs omit it.
    self._ctx.depth_mask = False  # ty: ignore[unresolved-attribute]
    try:
        self._vao.render()
    finally:
        self._ctx.depth_mask = True  # ty: ignore[unresolved-attribute]
```

This keeps the change local to the alpha-specific renderee and avoids cross-layer coupling or renderer orchestration changes.

- [ ] **Step 2: Re-run the red test file and verify GREEN**

Run: `uv run pytest tests/render/test_trimesh_renderee.py -v`

Expected: PASS

- [ ] **Step 3: Run adjacent validation for the touched render layer**

Run: `uv run pytest tests/render/test_renderer.py tests/render/test_label_renderee.py -v`

Expected: PASS

- [ ] **Step 4: Run formatting, linting, and targeted type checks**

Run: `uv run ruff format src/scadview/render/trimesh_renderee.py tests/render/test_trimesh_renderee.py`

Run: `uv run ruff check src/scadview/render/trimesh_renderee.py tests/render/test_trimesh_renderee.py`

Run: `uv run --no-sync ty check --exclude src/scadview/ui/wx --force-exclude`

Expected: all commands PASS

- [ ] **Step 5: Commit the implementation**

```bash
git add src/scadview/render/trimesh_renderee.py tests/render/test_trimesh_renderee.py
git commit -m "fix: restore depth mask after alpha rendering"
```

### Task 3: Manual verification note for follow-up

**Files:**
- No code changes required

- [ ] **Step 1: Manually verify mixed opaque/alpha rendering**

Open a model or fixture that contains both opaque and semi-transparent meshes and confirm:

1. Opaque geometry rendered after alpha geometry still writes depth correctly.
2. Camera motion still re-sorts alpha triangles without artifacts.
3. No visual regression appears in axes, labels, or gnomon overlays.

Suggested command: `uv run scadview`

Expected: human visual confirmation only. This is required because the bug is a render-state leak and automated tests only prove the code-level state reset.
