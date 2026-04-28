"""Feature mesh helpers.

Use features to mark optional geometry that SCADview can toggle in the UI.
Apply the decorator to mesh-returning functions or methods, not classes.
"""

from typing import Callable, ParamSpec, TypeVar, cast, overload

from manifold3d import Manifold
from trimesh import Trimesh

from scadview.features import FeatureMesh
from scadview.features import feature as _feature

P = ParamSpec("P")
TNativeMesh = TypeVar("TNativeMesh", Trimesh, Manifold)


@overload
def feature(name: str, mesh: TNativeMesh) -> FeatureMesh: ...


@overload
def feature(func: Callable[P, TNativeMesh]) -> Callable[P, FeatureMesh]: ...


@overload
def feature(
    name: str,
) -> Callable[[Callable[P, TNativeMesh]], Callable[P, FeatureMesh]]: ...


def feature(
    name_or_func: str | Callable[P, TNativeMesh],
    mesh: TNativeMesh | None = None,
) -> (
    FeatureMesh
    | Callable[P, FeatureMesh]
    | Callable[[Callable[P, TNativeMesh]], Callable[P, FeatureMesh]]
):
    """Mark a mesh or mesh-returning function or method as a named feature.

    Args:
        name_or_func: Feature name shown in the UI, or a decorated mesh factory.
        mesh: Mesh controlled by the feature toggle when calling the function form.

    Returns:
        A feature mesh proxy, or a decorator that wraps a mesh-producing
        function or method.
    """
    if mesh is not None:
        if not isinstance(name_or_func, str):
            raise TypeError("Expected feature name to be a string")
        return _feature(name_or_func, mesh)
    if isinstance(name_or_func, str):
        return cast(
            Callable[[Callable[P, TNativeMesh]], Callable[P, FeatureMesh]],
            _feature(name_or_func),
        )
    return cast(
        Callable[P, FeatureMesh],
        _feature(name_or_func),
    )
