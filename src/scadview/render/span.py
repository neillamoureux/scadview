from __future__ import annotations

import numpy as np


class Span:
    def __init__(self, initial_min: float = -np.inf, initial_max: float = np.inf):
        self._min = np.float32(initial_min)
        self._max = np.float32(initial_max)

    def is_empty(self) -> np.bool:
        return self._min > self._max

    @property
    def min(self) -> np.float32:
        if self.is_empty():
            raise ValueError("AxisRange is empty, no minimum value")
        return self._min

    @property
    def max(self) -> np.float32:
        if self.is_empty():
            raise ValueError("AxisRange is empty, no minimum value")
        return self._max

    def intersect(self, other: Span) -> Span:
        if self.is_empty() or other.is_empty():
            return EmptySpan()
        new_min = np.maximum(self._min, other._min)
        new_max = np.minimum(self._max, other._max)
        return Span(new_min, new_max)

    def __eq__(self, other: object):
        if not isinstance(other, Span):
            return False
        if self.is_empty() and other.is_empty():
            return True
        if self.is_empty() != other.is_empty():
            return False
        return self.min == other.min and self.max == other.max


class EmptySpan(Span):
    def __init__(self):
        super().__init__(np.inf, -np.inf)

    def is_empty(self) -> np.bool:
        return np.bool(True)
