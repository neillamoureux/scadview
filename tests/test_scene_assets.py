from dataclasses import FrozenInstanceError

import numpy as np
import pytest
from trimesh.creation import box

from scadview.mesh_payload import MeshPayload, mesh_to_payload
from scadview.scene_assets import SceneAssets, create_scene_assets


def test_scene_assets_are_complete_and_immutable():
    payload = mesh_to_payload(box())
    assets = SceneAssets(payload, payload, payload)

    assert assets.startup_mesh is payload
    assert assets.loading_mesh is payload
    assert assets.base_axes is payload
    with pytest.raises(FrozenInstanceError):
        assets.startup_mesh = payload


def test_scene_assets_normalize_each_source_mesh_to_a_payload(monkeypatch):
    source = box(extents=(2.0, 3.0, 4.0))
    monkeypatch.setattr(
        "scadview.scene_assets.create_startup_source_mesh", lambda: source
    )
    monkeypatch.setattr(
        "scadview.scene_assets.create_loading_source_mesh", lambda: source
    )
    monkeypatch.setattr(
        "scadview.scene_assets.create_base_axes_source_mesh", lambda: source
    )

    assets = create_scene_assets()

    assert all(
        isinstance(payload, MeshPayload)
        for payload in (assets.startup_mesh, assets.loading_mesh, assets.base_axes)
    )
    np.testing.assert_allclose(assets.base_axes.vertices, source.vertices)
