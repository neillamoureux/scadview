from dataclasses import dataclass

import pytest
from manifold3d import Manifold
from trimesh.creation import box

from scadview.features import (
    FeatureState,
    feature,
    get_feature_states,
    set_enabled_feature_states,
)


def teardown_function():
    set_enabled_feature_states(None)


def test_feature_registers_enabled_state_by_default():
    optional_mesh = feature("lid", box())

    assert optional_mesh.enabled
    assert get_feature_states() == [FeatureState("lid", True)]


def test_feature_decorator_uses_function_name_by_default():
    @feature
    def lid():
        return box()

    optional_mesh = lid()

    assert optional_mesh.name == "lid"
    assert optional_mesh.enabled
    assert get_feature_states() == [FeatureState("lid", True)]


def test_feature_decorator_accepts_explicit_name():
    @feature("custom-lid")
    def lid():
        return box()

    optional_mesh = lid()

    assert optional_mesh.name == "custom-lid"
    assert get_feature_states() == [FeatureState("custom-lid", True)]


def test_feature_decorator_supports_methods():
    @dataclass
    class LidBuilder:
        size: float

        @feature("lid")
        def mesh(self):
            return box([self.size, self.size, self.size])

    optional_mesh = LidBuilder(2.0).mesh()

    assert optional_mesh.name == "lid"
    assert get_feature_states() == [FeatureState("lid", True)]


def test_feature_decorator_rejects_classes():
    with pytest.raises(TypeError, match="not classes"):

        @feature
        @dataclass
        class Lid:
            size: float


def test_feature_decorator_rejects_non_mesh_return_values():
    @feature
    def not_a_mesh():
        return "nope"

    with pytest.raises(TypeError, match="must return Trimesh or Manifold"):
        not_a_mesh()


def test_disabled_feature_is_identity_for_trimesh_boolean_methods():
    set_enabled_feature_states({"cutout": False})
    base = box()
    optional = feature("cutout", box())

    assert base.union(optional) is base
    assert base.intersection(optional) is base
    assert base.difference(optional) is base
    assert optional.union(base) is base
    assert optional.intersection(base) is base
    assert optional.difference(base) is base


def test_disabled_feature_is_identity_for_manifold_boolean_operators():
    set_enabled_feature_states({"cutout": False})
    base = Manifold.cube()
    optional = feature("cutout", Manifold.cube())

    assert (base + optional) is base
    assert (base ^ optional) is base
    assert (base - optional) is base
    assert (optional + base) is base
    assert (optional ^ base) is base
    assert (optional - base) is base


def test_disabled_feature_chain_returns_null_feature_mesh():
    set_enabled_feature_states({"platform": False, "guide": False})
    platform = feature("platform", box())
    guide = feature("guide", box())

    result = platform.union(guide).difference(box())

    assert result.resolve() is None
