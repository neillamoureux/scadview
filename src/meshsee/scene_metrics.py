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
        return lower_bound
    if log_lower_bound > floor(log_lower_bound) + LABEL_FIVES_BREAK:
        return 10 ** (floor(log_lower_bound) + 1)
    if log_lower_bound > floor(log_lower_bound) + LABEL_TWOS_BREAK:
        return 5 * 10 ** (floor(log_lower_bound))
    return 2 * 10 ** (floor(log_lower_bound))


def label_round(value: float, step: float) -> float:
    """
    Round the value to the nearest multiple of the step size.
    """
    if step <= 0:
        raise ValueError("Step size must be greater than 0")
    return round(value / step) * step


def label_decimals(step: float) -> int:
    return int(-floor(log10(step))) if step < 1 else 0


def label_format(value: float, step: float) -> str:
    """
    Format the value as a string with the appropriate number of decimals.
    The number of decimals is calculated based on the step size.
    """
    decimals = label_decimals(step)
    if decimals == 0:
        return str(int(value))
    return f"{value:.{decimals}f}"


def label_char_width(
    min_value: float, max_value: float, step: float, fraction: float
) -> float:
    """
    Calculate the width of the label in world dimension.
    The width is calculated based on the number of characters in the label.
    """
    label_min = ceil(min_value / step) * step
    label_max = floor(max_value / step) * step
    label_min_len = len(label_format(label_min, step))
    label_max_lem = len(label_format(label_max, step))
    label_len = max(label_min_len, label_max_lem)
    return fraction * step / label_len


def labels_to_show(min_value: float, max_value: float, step: float) -> list[str]:
    """
    Generate a list of labels to show on the axis.
    The labels are generated based on the range and the step size.
    """

    labels = []
    label_min = ceil(min_value / step) * step
    label_max = floor(max_value / step) * step
    i = 0
    while label_min + i * step <= label_max:
        labels.append(label_format(label_round(label_min + i * step, step), step))
        i += 1
    return labels


class SceneMetrics:
    def __init__(self, camera: Camera):
        self.camera = camera

    def axis_visible_range(self, axis: int):
        return self.camera.axis_visible_range(axis)

    def labels_to_show(min: float, max: float, max_labels: int) -> list[float]:
        return []
