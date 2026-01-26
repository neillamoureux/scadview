from pytest import mark

from scadview.render.span import EmptySpan, Span


def test_equal():
    ar1 = Span(0, 1)
    ar2 = Span(0, 1)
    assert ar1 == ar2

    ar3 = Span(0, 2)
    assert ar1 != ar3

    ar4 = EmptySpan()
    ar5 = EmptySpan()
    assert ar4 == ar5

    assert ar1 != ar4

    assert ar1 != (0, 1)  # Different type


@mark.parametrize(
    "range1, range2, expected",
    [
        ((0, 1), (0.5, 1.5), (0.5, 1)),
        ((0, 1), (0, 1), (0, 1)),
        ((0, 1), (1, 2), (1, 1)),
        ((0, 1), (2, 3), EmptySpan),
        ((0, 1), (0.5, 0.5), (0.5, 0.5)),
        ((0, 1), (-0.5, 0.5), (0, 0.5)),
        ((0, 1), (-0.5, -0.1), EmptySpan),
    ],
)
def test_intersect(range1, range2, expected):
    ar1 = Span(range1[0], range1[1])
    ar2 = Span(range2[0], range2[1])
    ex = Span(expected[0], expected[1]) if expected != EmptySpan else EmptySpan()
    actual = ar1.intersect(ar2)
    assert actual == ex


def test_no_overlap():
    ar1 = Span(0, 1)
    ar2 = Span(2, 3)
    actual = ar1.intersect(ar2)
    assert actual.is_empty()
    assert actual == EmptySpan()


def test_intersect_with_empty():
    ar1 = Span(0, 1)
    ar2 = EmptySpan()
    actual = ar1.intersect(ar2)
    assert actual.is_empty()
    assert actual == EmptySpan()


def test_intersect_with_empty2():
    ar1 = Span(0, 1)
    ar2 = EmptySpan()
    actual = ar2.intersect(ar1)
    assert actual.is_empty()
    assert actual == EmptySpan()
