from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ViewName = Literal["frame", "xyz", "x", "y", "z"]
CameraName = Literal["perspective", "orthogonal"]


@dataclass(frozen=True)
class ViewState:
    view: ViewName
    camera: CameraName
    grid: bool
    axes: bool
    edges: bool
    gnomon: bool
