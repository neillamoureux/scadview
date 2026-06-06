# Issue 153 Problem 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent unbounded `LabelSetRenderee` cache growth by evicting label renderees not used in the current render pass while preserving reuse for visible labels.

**Architecture:** Keep the fix isolated to the render layer. `LabelSetRenderee` will track which labels were rendered in the current frame and prune stale cached renderees after the frame completes, releasing only resources owned by the evicted `LabelRenderee`.

**Tech Stack:** Python, pytest, unittest.mock, ModernGL-style resource objects

---

### Task 1: Add failing cache lifecycle tests

**Files:**
- Create: `tests/render/test_label_renderee.py`
- Test: `tests/render/test_label_renderee.py`

- [ ] **Step 1: Write the failing tests**

```python
from unittest.mock import MagicMock, call, patch

from scadview.render.label_renderee import LabelSetRenderee, _AxisSpan
from scadview.render.span import Span


def _make_label_set_renderee() -> LabelSetRenderee:
    return LabelSetRenderee(
        MagicMock(),
        MagicMock(),
        MagicMock(),
        max_labels_per_axis=20,
        max_label_frac_of_step=0.5,
        camera=MagicMock(),
    )


def _make_renderee(label: str) -> MagicMock:
    renderee = MagicMock()
    renderee.label = label
    return renderee


def test_render_prunes_cached_labels_not_used_in_current_frame():
    label_set = _make_label_set_renderee()
    first = _make_renderee("1")
    second = _make_renderee("2")

    with (
        patch.object(
            label_set,
            "_get_visible_axis_spans",
            return_value=[_AxisSpan(0, Span(0, 10))],
        ),
        patch.object(label_set, "_calc_label_step", return_value=1.0),
        patch.object(label_set, "_calc_char_width", return_value=0.5),
        patch("scadview.render.label_renderee.labels_to_show") as labels_to_show,
        patch("scadview.render.label_renderee.LabelRenderee") as renderee_cls,
    ):
        labels_to_show.side_effect = [["1"], ["2"]]
        renderee_cls.side_effect = [first, second]

        label_set.render()
        label_set.render()

    assert label_set._label_renderees == {"2": second}
    first._release_gl_resources.assert_called_once_with()


def test_render_keeps_cached_labels_used_in_current_frame():
    label_set = _make_label_set_renderee()
    first = _make_renderee("1")

    with (
        patch.object(
            label_set,
            "_get_visible_axis_spans",
            return_value=[_AxisSpan(0, Span(0, 10))],
        ),
        patch.object(label_set, "_calc_label_step", return_value=1.0),
        patch.object(label_set, "_calc_char_width", return_value=0.5),
        patch("scadview.render.label_renderee.labels_to_show", return_value=["1"]),
        patch("scadview.render.label_renderee.LabelRenderee", return_value=first),
    ) as _:
        label_set.render()
        label_set.render()

    assert label_set._label_renderees == {"1": first}
    first._release_gl_resources.assert_not_called()


def test_render_deduplicates_label_usage_across_axes():
    label_set = _make_label_set_renderee()
    shared = _make_renderee("1")

    with (
        patch.object(
            label_set,
            "_get_visible_axis_spans",
            return_value=[_AxisSpan(0, Span(0, 10)), _AxisSpan(1, Span(0, 10))],
        ),
        patch.object(label_set, "_calc_label_step", return_value=1.0),
        patch.object(label_set, "_calc_char_width", return_value=0.5),
        patch("scadview.render.label_renderee.labels_to_show", return_value=["1"]),
        patch("scadview.render.label_renderee.LabelRenderee", return_value=shared),
    ):
        label_set.render()

    assert label_set._label_renderees == {"1": shared}
    assert shared.render.call_count == 2
    shared._release_gl_resources.assert_not_called()


def test_pruned_label_renderees_are_cleaned_up():
    label_set = _make_label_set_renderee()
    keep = _make_renderee("2")
    stale = _make_renderee("1")
    label_set._label_renderees["1"] = stale

    with (
        patch.object(
            label_set,
            "_get_visible_axis_spans",
            return_value=[_AxisSpan(0, Span(0, 10))],
        ),
        patch.object(label_set, "_calc_label_step", return_value=1.0),
        patch.object(label_set, "_calc_char_width", return_value=0.5),
        patch("scadview.render.label_renderee.labels_to_show", return_value=["2"]),
        patch("scadview.render.label_renderee.LabelRenderee", return_value=keep),
    ):
        label_set.render()

    stale._release_gl_resources.assert_called_once_with()


def test_empty_visible_spans_do_not_prune_or_crash():
    label_set = _make_label_set_renderee()
    cached = _make_renderee("1")
    label_set._label_renderees["1"] = cached

    with patch.object(label_set, "_get_visible_axis_spans", return_value=[]):
        label_set.render()

    assert label_set._label_renderees == {"1": cached}
    cached._release_gl_resources.assert_not_called()
```

- [ ] **Step 2: Run the new test file and verify RED**

Run: `pytest tests/render/test_label_renderee.py -v`
Expected: FAIL because stale cached labels are not evicted and cleanup is never called.

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/render/test_label_renderee.py plans/2026-06-05-issue-153-label-cache-cleanup.md
git commit -m "test: add label cache cleanup regression tests"
```

### Task 2: Implement active-label cache pruning

**Files:**
- Modify: `src/scadview/render/label_renderee.py`
- Test: `tests/render/test_label_renderee.py`

- [ ] **Step 1: Add minimal implementation**

```python
def render(self):
    visible_axis_spans = self._get_visible_axis_spans()
    if len(visible_axis_spans) == 0:
        return
    step = self._calc_label_step(visible_axis_spans)
    char_width = self._calc_char_width(visible_axis_spans, step)
    active_labels: set[str] = set()
    self._render_labels(visible_axis_spans, step, char_width, active_labels)
    self._prune_inactive_labels(active_labels)
```

```python
def _release_gl_resources(self) -> None:
    ...
```

- [ ] **Step 2: Run the targeted tests and verify GREEN**

Run: `pytest tests/render/test_label_renderee.py -v`
Expected: PASS

- [ ] **Step 3: Run adjacent render tests**

Run: `pytest tests/render/test_renderer.py tests/render/test_label_metrics.py -v`
Expected: PASS

- [ ] **Step 4: Commit the implementation**

```bash
git add src/scadview/render/label_renderee.py tests/render/test_label_renderee.py
git commit -m "fix: prune inactive label renderees"
```
