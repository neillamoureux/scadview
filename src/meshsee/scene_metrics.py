from math import ceil, floor, log10

from meshsee.camera import Camera

LABEL_TENS_BREAK = 1.0
LABEL_FIVES_BREAK = log10(5)
LABEL_TWOS_BREAK = log10(2)


def label_step(span: float, max_labels: int) -> float:
    """
    Calculate the step size for the labels on the axis.
    The step size is calculated based on the range and the number of labels.
    The step size is a power or 10, or 2 * a power of 10 or 5 * a power of 10.
    range / step_size <= labels
    """
    if max_labels <= 0:
        raise ValueError("Number of labels must be greater than 0")
    if span <= 0:
        raise ValueError("Range must be greater than 0")
    lower_bound = span / max_labels
    log_lower_bound = log10(lower_bound)
    if log_lower_bound == ceil(log_lower_bound):
        return 10**log_lower_bound
    if log_lower_bound > floor(log_lower_bound) + LABEL_FIVES_BREAK:
        return 10 ** (floor(log_lower_bound) + 1)
    if log_lower_bound > floor(log_lower_bound) + LABEL_TWOS_BREAK:
        return 10 ** (floor(log_lower_bound) + LABEL_FIVES_BREAK)
    return 10 ** (floor(log_lower_bound) + LABEL_TWOS_BREAK)


class SceneMetrics:
    def __init__(self, camera: Camera):
        self.camera = camera

    def axis_visible_range(self, axis: int):
        return self.camera.axis_visible_range(axis)

    def labels_to_show(min: float, max: float, max_labels: int) -> list[float]:
        return []
