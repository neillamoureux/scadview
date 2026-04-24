from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
import inspect
from typing import Any, Callable, ParamSpec, TypeAlias, TypeVar, cast, overload

from manifold3d import Manifold
from trimesh import Trimesh

FeatureNativeMesh: TypeAlias = Trimesh | Manifold
FeatureNativeMeshOrNone: TypeAlias = FeatureNativeMesh | None
P = ParamSpec("P")
TNativeMesh = TypeVar("TNativeMesh", Trimesh, Manifold)


@dataclass(frozen=True)
class FeatureState:
    name: str
    enabled: bool = True


class NullFeatureMesh:
    def resolve(self) -> None:
        return None

    def union(self, other: Any) -> Any:
        return _identity_for_disabled_feature(other)

    def difference(self, _other: Any) -> NullFeatureMesh:
        return self

    def intersection(self, _other: Any) -> NullFeatureMesh:
        return self

    def __add__(self, other: Any) -> Any:
        return _identity_for_disabled_feature(other)

    def __sub__(self, _other: Any) -> NullFeatureMesh:
        return self

    def __xor__(self, _other: Any) -> NullFeatureMesh:
        return self


class FeatureMesh:
    def __init__(self, name: str, mesh: FeatureNativeMesh, enabled: bool):
        self._name = name
        self._mesh = mesh
        self._enabled = enabled

    @property
    def name(self) -> str:
        return self._name

    @property
    def enabled(self) -> bool:
        return self._enabled

    def resolve(self) -> FeatureNativeMeshOrNone:
        if self._enabled:
            return self._mesh
        return None

    def union(self, other: Any) -> Any:
        if not hasattr(self._mesh, "union"):
            raise AttributeError(
                f"{type(self._mesh).__name__!s} has no attribute 'union'"
            )
        return self._call_native_operation("union", other)

    def difference(self, other: Any) -> Any:
        if not hasattr(self._mesh, "difference"):
            raise AttributeError(
                f"{type(self._mesh).__name__!s} has no attribute 'difference'"
            )
        return self._call_native_operation("difference", other)

    def intersection(self, other: Any) -> Any:
        if not hasattr(self._mesh, "intersection"):
            raise AttributeError(
                f"{type(self._mesh).__name__!s} has no attribute 'intersection'"
            )
        return self._call_native_operation("intersection", other)

    def __add__(self, other: Any) -> Any:
        return self._call_native_operator("__add__", other)

    def __sub__(self, other: Any) -> Any:
        return self._call_native_operator("__sub__", other)

    def __xor__(self, other: Any) -> Any:
        return self._call_native_operator("__xor__", other)

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._mesh, name)
        if not callable(attr):
            return attr

        @wraps(attr)
        def _wrapped(*args: Any, **kwargs: Any) -> Any:
            result = attr(*args, **kwargs)
            if _is_native_mesh(result):
                return FeatureMesh(self._name, result, self._enabled)
            return result

        return _wrapped

    def _call_native_operation(self, name: str, other: Any) -> Any:
        if not self._enabled:
            return _identity_for_disabled_feature(other)
        resolved_other = _resolve_operand(other)
        if resolved_other is None:
            return self._mesh
        return getattr(self._mesh, name)(resolved_other)

    def _call_native_operator(self, name: str, other: Any) -> Any:
        if not self._enabled:
            return _identity_for_disabled_feature(other)
        resolved_other = _resolve_operand(other)
        if resolved_other is None:
            return self._mesh
        return getattr(self._mesh, name)(resolved_other)


class _FeatureContext:
    def __init__(self):
        self._states: dict[str, bool] = {}
        self._order: list[str] = []

    def set_enabled_states(self, states: dict[str, bool] | None):
        self._states = {} if states is None else dict(states)
        self._order = []

    def register(self, name: str) -> bool:
        if name not in self._order:
            self._order.append(name)
        return self._states.get(name, True)

    def states(self) -> list[FeatureState]:
        return [
            FeatureState(name, self._states.get(name, True)) for name in self._order
        ]


_FEATURE_CONTEXT = _FeatureContext()
_PATCHED_MEMBERS: set[tuple[type[Any], str]] = set()
_NATIVE_BOOLEAN_MEMBERS: dict[type[Any], tuple[str, ...]] = {
    Trimesh: ("union", "difference", "intersection"),
    Manifold: ("__add__", "__sub__", "__xor__"),
}


def set_enabled_feature_states(states: dict[str, bool] | None) -> None:
    _FEATURE_CONTEXT.set_enabled_states(states)


def get_feature_states() -> list[FeatureState]:
    return _FEATURE_CONTEXT.states()


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
    if mesh is not None:
        if not isinstance(name_or_func, str):
            raise TypeError("Expected feature name to be a string")
        return _feature_mesh(name_or_func, mesh)

    if isinstance(name_or_func, str):
        return cast(
            Callable[[Callable[P, TNativeMesh]], Callable[P, FeatureMesh]],
            _feature_decorator(name_or_func),
        )

    if callable(name_or_func):
        if inspect.isclass(name_or_func):
            raise TypeError(
                "@feature only supports mesh-returning functions or methods, "
                "not classes"
            )
        func = cast(Callable[P, TNativeMesh], name_or_func)
        feature_name = getattr(func, "__name__", "feature")
        return cast(
            Callable[P, FeatureMesh],
            _feature_decorator(feature_name)(func),
        )

    raise TypeError("Expected feature to be called with a name, mesh, or function")


def _feature_mesh(name: str, mesh: FeatureNativeMesh) -> FeatureMesh:
    enabled = _FEATURE_CONTEXT.register(name)
    return FeatureMesh(name, mesh, enabled)


def _feature_decorator(
    name: str,
) -> Callable[[Callable[P, TNativeMesh]], Callable[P, FeatureMesh]]:
    def _decorate(func: Callable[P, TNativeMesh]) -> Callable[P, FeatureMesh]:
        @wraps(func)
        def _wrapped(*args: P.args, **kwargs: P.kwargs) -> FeatureMesh:
            mesh = func(*args, **kwargs)
            if not _is_native_mesh(mesh):
                raise TypeError(
                    "@feature-decorated functions must return Trimesh or Manifold, "
                    f"got {type(mesh)}"
                )
            return _feature_mesh(name, mesh)

        return _wrapped

    return _decorate


def _identity_for_disabled_feature(other: Any) -> Any:
    resolved_other = _resolve_operand(other)
    if resolved_other is not None:
        return resolved_other
    return NullFeatureMesh()


def _resolve_operand(value: Any) -> FeatureNativeMeshOrNone | Any:
    if isinstance(value, FeatureMesh):
        return value.resolve()
    if isinstance(value, NullFeatureMesh):
        return None
    return value


def _is_native_mesh(value: Any) -> bool:
    return isinstance(value, Trimesh | Manifold)


def _patch_native_boolean_members() -> None:
    for cls, member_names in _NATIVE_BOOLEAN_MEMBERS.items():
        for member_name in member_names:
            key = (cls, member_name)
            if key in _PATCHED_MEMBERS:
                continue
            if not hasattr(cls, member_name):
                continue
            original = getattr(cls, member_name)

            def _patched(
                self: Any,
                other: Any,
                _original: Callable[..., Any] = original,
            ) -> Any:
                resolved_other = _resolve_operand(other)
                if resolved_other is None:
                    return self
                return _original(self, resolved_other)

            setattr(cls, member_name, _patched)
            _PATCHED_MEMBERS.add(key)


_patch_native_boolean_members()
