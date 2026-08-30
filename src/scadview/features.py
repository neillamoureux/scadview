from __future__ import annotations

import inspect
from dataclasses import dataclass
from functools import wraps
from typing import (
    Any,
    Callable,
    ParamSpec,
    TypeAlias,
    TypeVar,
    cast,
    overload,
)

from manifold3d import Manifold
from trimesh import Trimesh

FeatureNativeMesh: TypeAlias = Trimesh | Manifold
P = ParamSpec("P")
TNativeMesh = TypeVar("TNativeMesh", Trimesh, Manifold)


@dataclass(frozen=True)
class FeatureState:
    name: str
    enabled: bool = True


@dataclass(frozen=True)
class FeatureSource:
    name: str
    mesh: FeatureNativeMesh
    enabled: bool


class NullFeatureMesh:
    def as_operand(self) -> NullFeatureMesh:
        return self

    def is_empty(self) -> bool:
        return True

    def union(self, other: Any) -> Any:
        operand = _to_boolean_operand(other)
        if isinstance(operand, NullFeatureMesh):
            return self
        return operand.native()

    def difference(self, _other: Any) -> NullFeatureMesh:
        return self

    def intersection(self, _other: Any) -> NullFeatureMesh:
        return self

    def __add__(self, other: Any) -> Any:
        return self.union(other)

    def __sub__(self, _other: Any) -> NullFeatureMesh:
        return self

    def __xor__(self, _other: Any) -> NullFeatureMesh:
        return self


class BooleanMesh:
    def __init__(self, mesh: FeatureNativeMesh) -> None:
        if not _is_native_mesh(mesh):
            raise TypeError(
                f"boolean mesh must be Trimesh or Manifold, got {type(mesh)}"
            )
        self._mesh = mesh

    def as_operand(self) -> BooleanMesh:
        return self

    def is_empty(self) -> bool:
        return False

    def native(self) -> FeatureNativeMesh:
        return self._mesh

    def union(self, other: Any) -> Any:
        mesh = _require_trimesh(self._mesh, "union")
        operand = _to_boolean_operand(other)
        if operand.is_empty():
            return mesh
        return mesh.union(_require_trimesh(_native(operand), "union"))

    def difference(self, other: Any) -> Any:
        mesh = _require_trimesh(self._mesh, "difference")
        operand = _to_boolean_operand(other)
        if operand.is_empty():
            return mesh
        return mesh.difference(_require_trimesh(_native(operand), "difference"))

    def intersection(self, other: Any) -> Any:
        mesh = _require_trimesh(self._mesh, "intersection")
        operand = _to_boolean_operand(other)
        if operand.is_empty():
            return NullFeatureMesh()
        return mesh.intersection(_require_trimesh(_native(operand), "intersection"))

    def __add__(self, other: Any) -> Any:
        mesh = _require_manifold(self._mesh, "+")
        operand = _to_boolean_operand(other)
        if operand.is_empty():
            return mesh
        return mesh + _require_manifold(_native(operand), "+")

    def __sub__(self, other: Any) -> Any:
        mesh = _require_manifold(self._mesh, "-")
        operand = _to_boolean_operand(other)
        if operand.is_empty():
            return mesh
        return mesh - _require_manifold(_native(operand), "-")

    def __xor__(self, other: Any) -> Any:
        mesh = _require_manifold(self._mesh, "^")
        operand = _to_boolean_operand(other)
        if operand.is_empty():
            return NullFeatureMesh()
        return mesh ^ _require_manifold(_native(operand), "^")


class FeatureMesh:
    def __init__(self, name: str, mesh: FeatureNativeMesh, enabled: bool) -> None:
        self._name = name
        self._mesh = mesh
        self._enabled = enabled

    @property
    def name(self) -> str:
        return self._name

    @property
    def enabled(self) -> bool:
        return self._enabled

    def as_operand(self) -> BooleanMesh | NullFeatureMesh:
        if self._enabled:
            return BooleanMesh(self._mesh)
        return NullFeatureMesh()

    def is_empty(self) -> bool:
        return self.as_operand().is_empty()

    def union(self, other: Any) -> Any:
        if not hasattr(self._mesh, "union"):
            raise AttributeError(
                f"{type(self._mesh).__name__!s} has no attribute 'union'"
            )
        return self.as_operand().union(other)

    def difference(self, other: Any) -> Any:
        if not hasattr(self._mesh, "difference"):
            raise AttributeError(
                f"{type(self._mesh).__name__!s} has no attribute 'difference'"
            )
        return self.as_operand().difference(other)

    def intersection(self, other: Any) -> Any:
        if not hasattr(self._mesh, "intersection"):
            raise AttributeError(
                f"{type(self._mesh).__name__!s} has no attribute 'intersection'"
            )
        return self.as_operand().intersection(other)

    def __add__(self, other: Any) -> Any:
        return self.as_operand() + other

    def __sub__(self, other: Any) -> Any:
        return self.as_operand() - other

    def __xor__(self, other: Any) -> Any:
        return self.as_operand() ^ other

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


class _FeatureContext:
    def __init__(self) -> None:
        self._states: dict[str, bool] = {}
        self._defaults: dict[str, bool] = {}
        self._order: list[str] = []
        self._sources: list[FeatureSource] = []

    def set_enabled_states(self, states: dict[str, bool] | None) -> None:
        self._states = {} if states is None else dict(states)
        self._defaults = {}
        self._order = []
        if states is None:
            self._sources = []

    def set_default(self, name: str, enabled: bool) -> None:
        if name in self._defaults and self._defaults[name] != enabled:
            raise ValueError(f"Conflicting default for feature {name!r}")
        self._defaults[name] = enabled

    def register(self, name: str) -> bool:
        if name not in self._order:
            self._order.append(name)
        return self._states.get(name, self._defaults.get(name, True))

    def states(self) -> list[FeatureState]:
        return [
            FeatureState(name, self._states.get(name, self._defaults.get(name, True)))
            for name in self._order
        ]

    def begin_capture(self) -> None:
        self._sources = []

    def capture(self, name: str, mesh: FeatureNativeMesh, enabled: bool) -> None:
        self._sources.append(FeatureSource(name, mesh, enabled))

    def sources(self) -> list[FeatureSource]:
        return list(self._sources)


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


def begin_feature_capture() -> None:
    _FEATURE_CONTEXT.begin_capture()


def get_feature_sources() -> list[FeatureSource]:
    return _FEATURE_CONTEXT.sources()


def feature_default(name: str, enabled: bool = True) -> None:
    _FEATURE_CONTEXT.set_default(name, enabled)


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
    if not _is_native_mesh(mesh):
        raise TypeError(f"feature mesh must be Trimesh or Manifold, got {type(mesh)}")
    enabled = _FEATURE_CONTEXT.register(name)
    _FEATURE_CONTEXT.capture(name, mesh, enabled)
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


def _to_boolean_operand(value: Any) -> BooleanMesh | NullFeatureMesh:
    if isinstance(value, FeatureMesh):
        return value.as_operand()
    if isinstance(value, BooleanMesh):
        return value
    if isinstance(value, NullFeatureMesh):
        return value
    return BooleanMesh(value)


def _native(operand: BooleanMesh | NullFeatureMesh) -> FeatureNativeMesh:
    if isinstance(operand, BooleanMesh):
        return operand.native()
    raise TypeError("Expected non-empty boolean operand")


def _has_feature_operand(value: Any) -> bool:
    return isinstance(value, FeatureMesh | NullFeatureMesh)


def _require_trimesh(mesh: FeatureNativeMesh, operation: str) -> Trimesh:
    if isinstance(mesh, Trimesh):
        return mesh
    raise TypeError(f"{operation} requires Trimesh operands")


def _require_manifold(mesh: FeatureNativeMesh, operation: str) -> Manifold:
    if isinstance(mesh, Manifold):
        return mesh
    raise TypeError(f"{operation} requires Manifold operands")


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
                _member_name: str = member_name,
            ) -> Any:
                if _has_feature_operand(other):
                    return getattr(BooleanMesh(self), _member_name)(other)
                return _original(self, other)

            setattr(cls, member_name, _patched)
            _PATCHED_MEMBERS.add(key)


_patch_native_boolean_members()
