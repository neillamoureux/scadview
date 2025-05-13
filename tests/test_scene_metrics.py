import pytest
from pytest import approx

from meshsee.scene_metrics import (
    label_char_width,
    label_decimals,
    label_format,
    label_round,
    label_step,
    labels_to_show,
)


@pytest.mark.parametrize(
    "span, max_labels, expected", [(10.0, 5, 2.0), (10.0, 1, 10.0), (200.0, 20, 10.0)]
)
def test_label_step_simple(span, max_labels, expected):
    assert label_step(span, max_labels) == approx(expected)


@pytest.mark.parametrize(
    "span, max_labels, expected",
    [(190, 20, 10.0), (180, 20, 10.0), (0.9, 10, 0.1), (100000, 100, 1000)],
)
def test_label_step_tens(span, max_labels, expected):
    assert label_step(span, max_labels) == approx(expected)


@pytest.mark.parametrize(
    "span, max_labels, expected", [(95, 20, 5.0), (100, 20, 5.0), (10000, 20, 500)]
)
def test_label_step_fives(span, max_labels, expected):
    assert label_step(span, max_labels) == expected


@pytest.mark.parametrize(
    "span, max_labels, expected",
    [
        (29, 15, 2.0),
        (1000, 50, 20.0),
    ],
)
def test_label_step_twos(span, max_labels, expected):
    assert label_step(span, max_labels) == expected


@pytest.mark.parametrize("span, max_labels", [(0, 5), (-1.0, 5), (10.0, 0), (10.0, -1)])
def test_label_step_value_errors(span, max_labels):
    with pytest.raises(ValueError):
        label_step(span, max_labels)


@pytest.mark.parametrize(
    "value, step, expected",
    [
        (10.001, 2.0, 10.0),
        (0.00101, 0.0002, 0.001),
        (-10.001, 2.0, -10.0),
    ],
)
def test_label_round(value, step, expected):
    assert label_round(value, step) == approx(expected)


def test_label_round_value_error():
    with pytest.raises(ValueError):
        label_round(10.0, -0.1)


@pytest.mark.parametrize(
    "step, expected", [(1.0, 0), (2.0, 0), (0.1, 1), (0.01, 2), (0.2, 1), (0.005, 3)]
)
def test_label_decimals(step, expected):
    assert label_decimals(step) == approx(expected)


@pytest.mark.parametrize(
    "value, step, expected",
    [(10.001, 2.0, "10"), (0.00101, 0.0002, "0.0010"), (-10.001, 2.0, "-10")],
)
def test_label_format(value, step, expected):
    assert label_format(value, step) == approx(expected)


@pytest.mark.parametrize(
    "min_value, max_value, step, fraction, expected",
    [(0, 10, 2, 0.5, 0.5), (-212, 55.0, 20.0, 0.3, 1.5)],
)
def test_label_char_width(min_value, max_value, step, fraction, expected):
    # Test case with a range of 10 and a step size of 2
    assert label_char_width(min_value, max_value, step, fraction) == approx(expected)


@pytest.mark.parametrize(
    "min_value, max_value, step, expected",
    [
        (-20.0, 20.0, 10.0, ["-20", "-10", "10", "20"]),
    ],
)
def test_labels_to_show(min_value, max_value, step, expected):
    assert labels_to_show(min_value, max_value, step) == expected
