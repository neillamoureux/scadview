import tomllib
from pathlib import Path
from textwrap import dedent

import pytest

from tests.tools.docs_screenshots_test_support import (
    fail_on_wx_import,
    screenshot_block,
    screenshot_blocks,
    write_valid_docs_tree,
)


def test_fixture_manifest_lists_expected_screenshot_entry_fields(tmp_path):
    manifest_path = write_valid_docs_tree(tmp_path)

    payload = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    names = [entry["name"] for entry in payload["screenshots"]]

    assert names[0] == "grid"
    assert "grid" in names
    assert "sphere" in names
    for entry in payload["screenshots"]:
        assert set(entry) == {
            "axes",
            "camera",
            "edges",
            "gnomon",
            "grid",
            "module",
            "name",
            "output",
            "view",
            "window_size",
        }


def test_tools_package_exposes_docs_screenshots_check_module():
    import tools.docs_screenshots_check as docs_screenshots_check

    assert docs_screenshots_check.__name__ == "tools.docs_screenshots_check"


def test_validate_manifest_accepts_fixture_manifest_without_importing_wx(
    tmp_path, monkeypatch
):
    fail_on_wx_import(monkeypatch)

    from tools.docs_screenshots_check import validate_manifest

    manifest_path = write_valid_docs_tree(tmp_path)
    manifest = validate_manifest(
        manifest_path,
        repo_root=tmp_path,
    )

    names = [entry.name for entry in manifest.entries]
    assert names[0] == "grid"
    assert "grid" in names
    assert "sphere" in names


def test_load_manifest_parses_screenshot_entries(tmp_path):
    from tools.docs_screenshots_check import load_manifest

    manifest_path = write_valid_docs_tree(
        tmp_path,
        screenshots=[
            screenshot_block(
                "grid",
                "images/grid.png",
                "examples/sphere.py",
                view="xyz",
                camera="orthogonal",
            ),
            screenshot_block("sphere", "images/sphere.png", "examples/sphere.py"),
        ],
    )

    manifest = load_manifest(manifest_path)

    assert [entry.name for entry in manifest.entries] == ["grid", "sphere"]
    assert manifest.entries[0].output == Path("images/grid.png")
    assert manifest.entries[0].module == Path("examples/sphere.py")
    assert manifest.entries[0].window_size == (960, 720)
    assert manifest.entries[0].view == "xyz"
    assert manifest.entries[0].camera == "orthogonal"
    assert manifest.entries[0].grid is True
    assert manifest.entries[0].axes is True
    assert manifest.entries[0].edges is False
    assert manifest.entries[0].gnomon is True


def test_validate_manifest_accepts_selected_subset_without_importing_wx(
    tmp_path, monkeypatch
):
    manifest_path = write_valid_docs_tree(tmp_path)
    fail_on_wx_import(monkeypatch)

    from tools.docs_screenshots_check import validate_manifest

    manifest = validate_manifest(
        manifest_path,
        repo_root=tmp_path,
        selected_names={"sphere"},
    )

    assert [entry.name for entry in manifest.entries] == ["sphere"]


def test_validate_manifest_rejects_duplicate_names(tmp_path):
    from tools.docs_screenshots_check import ScreenshotManifestError, validate_manifest

    manifest_path = write_valid_docs_tree(
        tmp_path,
        screenshots=[
            screenshot_block("grid", "images/grid.png", "examples/sphere.py"),
            screenshot_block("grid", "images/grid-again.png", "examples/sphere.py"),
        ],
        markdown_refs=["docs/images/grid.png", "docs/images/grid-again.png"],
    )

    with pytest.raises(ScreenshotManifestError, match="duplicate.*grid"):
        validate_manifest(manifest_path, repo_root=tmp_path)


def test_validate_manifest_rejects_non_boolean_toggle_values(tmp_path):
    from tools.docs_screenshots_check import ScreenshotManifestError, validate_manifest

    manifest_path = write_valid_docs_tree(
        tmp_path,
        screenshots=[
            dedent(
                """
                [[screenshots]]
                name = "grid"
                output = "images/grid.png"
                module = "examples/sphere.py"
                window_size = [960, 720]
                view = "frame"
                camera = "perspective"
                grid = 1
                axes = true
                edges = false
                gnomon = true
                """
            ).strip()
        ],
    )

    with pytest.raises(ScreenshotManifestError, match="grid must be true or false"):
        validate_manifest(manifest_path, repo_root=tmp_path)


def test_validate_manifest_does_not_require_markdown_references(tmp_path):
    from tools.docs_screenshots_check import validate_manifest

    manifest_path = write_valid_docs_tree(
        tmp_path,
        screenshots=[
            screenshot_block("grid", "images/grid.png", "examples/sphere.py"),
        ],
        markdown_refs=[],
    )
    (tmp_path / "notes.md").write_text(
        "![Ignored](docs/images/grid.png)",
        encoding="utf-8",
    )

    manifest = validate_manifest(manifest_path, repo_root=tmp_path)

    assert [entry.name for entry in manifest.entries] == ["grid"]


@pytest.mark.parametrize(
    ("screenshot_specs", "markdown_refs", "selected_names", "match"),
    [
        (None, None, {"missing"}, "unknown.*missing"),
        (
            [("grid", "../images/grid.png", "examples/sphere.py", {})],
            ["../images/grid.png"],
            None,
            "output.*escape",
        ),
        (
            [("grid", "images/grid.png", "examples/missing.py", {})],
            ["docs/images/grid.png"],
            None,
            "module.*missing",
        ),
        (
            [("grid", "images/grid.png", "../examples/sphere.py", {})],
            ["docs/images/grid.png"],
            None,
            "module.*escape",
        ),
        (
            [("grid", "/tmp/grid.png", "examples/sphere.py", {})],
            ["docs/images/grid.png"],
            None,
            "path must be relative",
        ),
        (
            [("grid", "images/grid.png", "examples/sphere.py", {"view": "isometric"})],
            ["docs/images/grid.png"],
            None,
            "view.*isometric",
        ),
        (
            [("grid", "images/grid.png", "examples/sphere.py", {"camera": "fisheye"})],
            ["docs/images/grid.png"],
            None,
            "camera.*fisheye",
        ),
        (
            [
                (
                    "grid",
                    "images/grid.png",
                    "examples/sphere.py",
                    {"window_size": [960, 0]},
                )
            ],
            ["docs/images/grid.png"],
            None,
            "window_size",
        ),
        (
            [("grid", "images/grid.jpg", "examples/sphere.py", {})],
            ["docs/images/grid.jpg"],
            None,
            "PNG.*output",
        ),
    ],
)
def test_validate_manifest_rejects_invalid_manifest(
    tmp_path,
    screenshot_specs,
    markdown_refs,
    selected_names,
    match,
):
    from tools.docs_screenshots_check import (
        ScreenshotManifestError,
        validate_manifest,
    )

    screenshots = screenshot_blocks(screenshot_specs)
    manifest_path = write_valid_docs_tree(
        tmp_path,
        screenshots=screenshots,
        markdown_refs=markdown_refs,
    )

    with pytest.raises(ScreenshotManifestError, match=match):
        validate_manifest(
            manifest_path,
            repo_root=tmp_path,
            selected_names=selected_names,
        )


@pytest.mark.parametrize("view", ["frame", "xyz", "x", "y", "z"])
def test_validate_manifest_accepts_supported_view_values(tmp_path, view):
    from tools.docs_screenshots_check import validate_manifest

    manifest_path = write_valid_docs_tree(
        tmp_path,
        screenshots=[
            screenshot_block(
                "grid",
                "images/grid.png",
                "examples/sphere.py",
                view=view,
            ),
        ],
        markdown_refs=["docs/images/grid.png"],
    )

    manifest = validate_manifest(manifest_path, repo_root=tmp_path)

    assert manifest.entries[0].view == view


@pytest.mark.parametrize("camera", ["perspective", "orthogonal"])
def test_validate_manifest_accepts_supported_camera_values(tmp_path, camera):
    from tools.docs_screenshots_check import validate_manifest

    manifest_path = write_valid_docs_tree(
        tmp_path,
        screenshots=[
            screenshot_block(
                "grid",
                "images/grid.png",
                "examples/sphere.py",
                camera=camera,
            ),
        ],
        markdown_refs=["docs/images/grid.png"],
    )

    manifest = validate_manifest(manifest_path, repo_root=tmp_path)

    assert manifest.entries[0].camera == camera
