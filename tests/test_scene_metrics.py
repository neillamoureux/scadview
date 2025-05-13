import pytest
from pytest import approx

from meshsee.scene_metrics import label_round, label_step


@pytest.mark.parametrize(
    "span, max_labels, expected", [(10.0, 5, 2.0), (10.0, 1, 10.0), (200.0, 20, 10.0)]
)
def test_label_step_simple(span, max_labels, expected):
    assert label_step(span, max_labels) == approx(expected)


@pytest.mark.parametrize(
    "span, max_labels, expected", [(190, 20, 10.0), (180, 20, 10.0), [0.9, 10, 0.1]]
)
def test_label_step_tens(span, max_labels, expected):
    assert label_step(span, max_labels) == approx(expected)


@pytest.mark.parametrize("span, max_labels, expected", [(95, 20, 5.0), (100, 20, 5.0)])
def test_label_step_fives(span, max_labels, expected):
    assert label_step(span, max_labels) == approx(expected)


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
