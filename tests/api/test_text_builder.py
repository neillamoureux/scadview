import numpy as np
import pytest
import trimesh
from shapely.geometry import Polygon

from scadview.api import text_builder


def test_text_polys_returns_polygons():
    polys = text_builder.text_polys("Test", size=12)
    assert isinstance(polys, list)
    assert all(isinstance(p, Polygon) for p in polys)
    assert len(polys) > 0


def test_text_polys_spaces_only():
    polys = text_builder.text_polys("  ")
    assert isinstance(polys, list)
    assert isinstance(polys[0], Polygon)
    assert len(polys) == 1


def test_text_returns_trimesh_object():
    mesh = text_builder.text("Test", size=12)
    # Should be a trimesh.Trimesh object
    assert isinstance(mesh, trimesh.Trimesh)
    assert mesh.vertices.shape[1] == 3


def test_text_with_nonexistent_font_falls_back_to_default(monkeypatch):
    # Patch list_system_fonts to return empty dict
    monkeypatch.setattr(text_builder, "list_system_fonts", lambda: {})
    mesh = text_builder.text("Fallback", size=10, font="NonexistentFont")
    assert isinstance(mesh, trimesh.Trimesh)


def test_spaces_only(monkeypatch):
    monkeypatch.setattr(text_builder, "list_system_fonts", lambda: {})
    mesh = text_builder.text("  ")
    assert isinstance(mesh, trimesh.Trimesh)
    assert mesh.vertices.shape[0] == 0


def test_loops_from_text_alignment_variants():
    text = "A"
    font_path = text_builder.DEFAULT_FONT_PATH
    size = 10
    for halign in ["left", "center", "right"]:
        for valign in ["baseline", "top", "bottom", "center"]:
            loops = text_builder._loops_from_text(text, font_path, size, halign, valign)
            assert isinstance(loops, list)
            assert all(isinstance(loop, np.ndarray) for loop in loops)


def test_calc_offsets_and_x_y_offset():
    text = "Test"
    font_path = text_builder.DEFAULT_FONT_PATH
    fp = text_builder.FontProperties(fname=font_path, size=10)
    hal = {}
    for halign in ["left", "center", "right"]:
        hal[halign], _ = text_builder._calc_offsets(text, fp, halign, "baseline")
    assert hal["right"] < hal["center"] < hal["left"]
    assert hal["left"] == 0.0
    assert hal["center"] == pytest.approx(hal["right"] / 2.0)

    val = {}
    for valign in ["baseline", "top", "bottom", "center"]:
        _, val[valign] = text_builder._calc_offsets(text, fp, "left", valign)
    assert val["top"] < val["center"] < val["baseline"] < val["bottom"]
    assert val["baseline"] == 0.0
    assert val["center"] == pytest.approx((val["bottom"] + val["top"]) / 2.0)


def test_make_polys_and_track_containment_simple():
    # Two non-overlapping squares
    loops = [
        np.array([[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]),
        np.array([[2, 2], [2, 3], [3, 3], [3, 2], [2, 2]]),
    ]
    polys = text_builder._make_polys(loops)
    assert isinstance(polys, list)
    assert all(isinstance(p, Polygon) for p in polys)
    assert len(polys) == 2


def test_make_polys_with_hole():
    # Outer square and inner square (hole)
    outer = np.array([[0, 0], [0, 4], [4, 4], [4, 0], [0, 0]])
    inner = np.array([[1, 1], [1, 2], [2, 2], [2, 1], [1, 1]])
    loops = [outer, inner]
    polys = text_builder._make_polys(loops)
    assert len(polys) == 1
    assert polys[0].interiors
    assert np.allclose(polys[0].exterior.coords[:], outer)
    assert np.allclose(list(polys[0].interiors)[0].coords[:], inner)


def test_make_nested_polys_with_holes():
    # Outer square and inner square (hole)
    outer = np.array([[0, 0], [0, 4], [4, 4], [4, 0], [0, 0]])
    inner = np.array([[1, 1], [1, 2], [2, 2], [2, 1], [1, 1]])
    inner_2 = np.array(
        [[1.25, 1.25], [1.25, 1.75], [1.75, 1.75], [1.75, 1.25], [1.25, 1.25]]
    )
    inner_3 = np.array([[1.4, 1.4], [1.4, 1.6], [1.6, 1.6], [1.6, 1.4], [1.4, 1.4]])
    loops = [outer, inner, inner_2, inner_3]
    polys = text_builder._make_polys(loops)
    assert len(polys) == 2
    assert polys[0].interiors
    assert polys[1].interiors
    assert np.allclose(polys[0].exterior.coords[:], outer)
    assert np.allclose(list(polys[0].interiors)[0].coords[:], inner)
    assert np.allclose(polys[1].exterior.coords[:], inner_2)
    assert np.allclose(list(polys[1].interiors)[0].coords[:], inner_3)


def test_calc_x_offset_invalid():
    with pytest.raises(ValueError):
        text_builder._calc_x_offset("invalid", 10)


def test_calc_y_offset_invalid():
    with pytest.raises(ValueError):
        text_builder._calc_y_offset("invalid", 10, 2)


def test_text_direction_ltr_and_rtl(monkeypatch):
    # Patch list_system_fonts to return empty dict to force default font
    monkeypatch.setattr(text_builder, "list_system_fonts", lambda: {})
    # LTR should return a mesh
    mesh_ltr = text_builder.text("abc", direction="ltr")
    assert isinstance(mesh_ltr, trimesh.Trimesh)
    # RTL should reverse the text, but still return a mesh
    mesh_rtl = text_builder.text("abc", direction="rtl")
    assert isinstance(mesh_rtl, trimesh.Trimesh)
    # The meshes should not be identical (since text is reversed)
    assert not np.allclose(mesh_ltr.vertices, mesh_rtl.vertices)
    # Invalid direction should raise ValueError
    with pytest.raises(ValueError):
        text_builder.text("abc", direction="invalid")


def test_text_empty_string_returns_empty_mesh():
    mesh = text_builder.text("")
    assert isinstance(mesh, trimesh.Trimesh)
    assert mesh.vertices.shape[0] == 0
    assert mesh.faces.shape[0] == 0
