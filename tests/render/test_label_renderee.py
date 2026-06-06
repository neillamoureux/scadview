from unittest.mock import MagicMock, patch

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
    ):
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
