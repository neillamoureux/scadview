from dataclasses import dataclass

import pytest
from manifold3d import Manifold
from trimesh import Trimesh
from trimesh.creation import box

from scadview.features import (
    _NATIVE_BOOLEAN_MEMBERS,
    BooleanMesh,
    FeatureState,
    NullFeatureMesh,
    _native,
    _patch_native_boolean_members,
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


def test_feature_default_sets_name_level_default_state():
    from scadview.features import feature_default

    feature_default("supports", enabled=False)

    support_a = feature("supports", box())
    support_b = feature("supports", box())

    assert not support_a.enabled
    assert not support_b.enabled
    assert get_feature_states() == [FeatureState("supports", False)]


def test_feature_default_uses_enabled_when_no_default_is_declared():
    from scadview.features import feature_default

    feature_default("supports", enabled=False)

    lid = feature("lid", box())

    assert lid.enabled
    assert get_feature_states() == [FeatureState("lid", True)]


def test_feature_default_does_not_override_controller_state():
    from scadview.features import feature_default

    set_enabled_feature_states({"supports": True})
    feature_default("supports", enabled=False)

    support = feature("supports", box())

    assert support.enabled
    assert get_feature_states() == [FeatureState("supports", True)]


def test_feature_default_allows_idempotent_duplicate_declarations():
    from scadview.features import feature_default

    feature_default("supports", enabled=False)
    feature_default("supports", enabled=False)

    support = feature("supports", box())

    assert not support.enabled


def test_feature_default_rejects_conflicting_duplicate_declarations():
    from scadview.features import feature_default

    feature_default("supports", enabled=False)

    with pytest.raises(ValueError, match="Conflicting default"):
        feature_default("supports", enabled=True)


def test_feature_default_is_available_from_top_level_api():
    from scadview import feature_default

    feature_default("supports", enabled=False)

    support = feature("supports", box())

    assert not support.enabled


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


def test_feature_call_rejects_non_mesh_values():
    with pytest.raises(TypeError, match="feature mesh must be Trimesh or Manifold"):
        feature("lid", "nope")


def test_disabled_feature_has_side_aware_trimesh_boolean_methods():
    set_enabled_feature_states({"cutout": False})
    base = box()
    optional = feature("cutout", box())

    assert base.union(optional) is base
    assert base.difference(optional) is base
    assert optional.union(base) is base
    assert isinstance(base.intersection(optional), NullFeatureMesh)
    assert isinstance(optional.intersection(base), NullFeatureMesh)
    assert isinstance(optional.difference(base), NullFeatureMesh)


def test_disabled_feature_has_side_aware_manifold_boolean_operators():
    set_enabled_feature_states({"cutout": False})
    base = Manifold.cube()
    optional = feature("cutout", Manifold.cube())

    assert (base + optional) is base
    assert (base - optional) is base
    assert (optional + base) is base
    assert isinstance(base ^ optional, NullFeatureMesh)
    assert isinstance(optional ^ base, NullFeatureMesh)
    assert isinstance(optional - base, NullFeatureMesh)


def test_disabled_feature_chain_returns_null_feature_mesh():
    set_enabled_feature_states({"platform": False, "guide": False})
    platform = feature("platform", box())
    guide = feature("guide", box())

    result = platform.union(guide).difference(box())

    assert result.is_empty()


def test_boolean_mesh_operand_methods():
    mesh = BooleanMesh(box())

    assert mesh.as_operand() is mesh
    assert not mesh.is_empty()
    assert mesh.native() is not None


def test_null_feature_mesh_operand_methods():
    null_mesh = NullFeatureMesh()

    assert null_mesh.as_operand() is null_mesh
    assert null_mesh.is_empty()
    assert null_mesh.union(NullFeatureMesh()) is null_mesh
    assert null_mesh.difference(box()) is null_mesh
    assert null_mesh.intersection(box()) is null_mesh
    assert null_mesh + NullFeatureMesh() is null_mesh
    assert null_mesh - box() is null_mesh
    assert null_mesh ^ box() is null_mesh


def test_enabled_trimesh_boolean_methods_delegate_to_native_methods(monkeypatch):
    base = box()
    other = box()
    optional = feature("base", base)
    calls: list[tuple[str, Trimesh]] = []

    def union(self, operand):
        calls.append(("union", operand))
        return self

    def difference(self, operand):
        calls.append(("difference", operand))
        return self

    def intersection(self, operand):
        calls.append(("intersection", operand))
        return self

    monkeypatch.setattr(Trimesh, "union", union)
    monkeypatch.setattr(Trimesh, "difference", difference)
    monkeypatch.setattr(Trimesh, "intersection", intersection)

    assert optional.union(other) is base
    assert optional.difference(feature("other", other)) is base
    assert optional.intersection(BooleanMesh(other)) is base
    assert calls == [
        ("union", other),
        ("difference", other),
        ("intersection", other),
    ]


def test_enabled_manifold_boolean_operators_delegate_to_native_operators():
    base = Manifold.cube()
    other = Manifold.cube()
    optional = feature("base", base)

    assert isinstance(optional + other, Manifold)
    assert isinstance(optional - feature("other", other), Manifold)
    assert isinstance(optional ^ BooleanMesh(other), Manifold)


def test_feature_mesh_reports_empty_state():
    enabled = feature("enabled", box())
    set_enabled_feature_states({"disabled": False})
    disabled = feature("disabled", box())

    assert not enabled.is_empty()
    assert disabled.is_empty()


def test_feature_mesh_delegates_attributes_and_wraps_native_method_results():
    optional = feature("lid", box())

    assert optional.vertices.shape[1] == 3
    copied = optional.copy()
    assert copied.name == "lid"
    assert copied.enabled


def test_feature_mesh_delegated_methods_return_non_mesh_values():
    optional = feature("lid", box())

    assert isinstance(optional.export(file_type="stl"), bytes)


def test_feature_rejects_mesh_with_non_string_name():
    with pytest.raises(TypeError, match="Expected feature name to be a string"):
        feature(lambda: box(), box())


def test_feature_rejects_invalid_argument():
    with pytest.raises(TypeError, match="Expected feature"):
        feature(123)


def test_boolean_mesh_rejects_non_native_mesh():
    with pytest.raises(TypeError, match="boolean mesh must be Trimesh or Manifold"):
        BooleanMesh("nope")


def test_mixed_backend_operations_raise_clear_type_errors():
    trimesh_feature = feature("trimesh", box())
    manifold_feature = feature("manifold", Manifold.cube())

    with pytest.raises(TypeError, match="union requires Trimesh operands"):
        trimesh_feature.union(manifold_feature)
    with pytest.raises(TypeError, match="\\+ requires Manifold operands"):
        manifold_feature + trimesh_feature
    with pytest.raises(TypeError, match="\\+ requires Manifold operands"):
        trimesh_feature + manifold_feature


@pytest.mark.parametrize("method_name", ["union", "difference", "intersection"])
def test_manifold_feature_rejects_trimesh_boolean_methods(method_name):
    optional = feature("manifold", Manifold.cube())

    with pytest.raises(AttributeError, match=f"has no attribute '{method_name}'"):
        getattr(optional, method_name)(box())


def test_native_rejects_null_operand():
    with pytest.raises(TypeError, match="Expected non-empty boolean operand"):
        _native(NullFeatureMesh())


def test_patch_native_boolean_members_is_idempotent():
    _patch_native_boolean_members()


def test_patch_native_boolean_members_skips_missing_members():
    class NativeWithoutBooleans:
        pass

    _NATIVE_BOOLEAN_MEMBERS[NativeWithoutBooleans] = ("missing",)
    try:
        _patch_native_boolean_members()
    finally:
        del _NATIVE_BOOLEAN_MEMBERS[NativeWithoutBooleans]
