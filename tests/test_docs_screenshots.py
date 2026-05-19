import builtins
import importlib.util
import sys
import tomllib
from pathlib import Path
from textwrap import dedent

import pytest


def test_repository_manifest_lists_initial_screenshot_entries():
    manifest_path = Path("docs/screenshots.toml")

    payload = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    names = [entry["name"] for entry in payload["screenshots"]]

    assert names == [
        "startup_window",
        "grid",
        "edges",
        "sphere",
        "colors",
        "cube_minus_sphere",
    ]
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


def test_repository_manifest_validates_against_docs_without_importing_wx(monkeypatch):
    _fail_on_wx_import(monkeypatch)

    from scadview.docs_screenshots import validate_manifest

    manifest = validate_manifest(
        Path("docs/screenshots.toml"),
        repo_root=Path("."),
    )

    assert [entry.name for entry in manifest.entries] == [
        "startup_window",
        "grid",
        "edges",
        "sphere",
        "colors",
        "cube_minus_sphere",
    ]


def test_load_manifest_parses_screenshot_entries(tmp_path):
    from scadview.docs_screenshots import load_manifest

    manifest_path = _write_valid_docs_tree(
        tmp_path,
        screenshots=[
            _screenshot_block(
                "grid",
                "images/grid.png",
                "examples/sphere.py",
                view="xyz",
                camera="orthogonal",
            ),
            _screenshot_block("sphere", "images/sphere.png", "examples/sphere.py"),
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
    manifest_path = _write_valid_docs_tree(tmp_path)
    _fail_on_wx_import(monkeypatch)

    from scadview.docs_screenshots import validate_manifest

    manifest = validate_manifest(
        manifest_path,
        repo_root=tmp_path,
        selected_names={"sphere"},
    )

    assert [entry.name for entry in manifest.entries] == ["sphere"]


def test_validate_manifest_rejects_duplicate_names(tmp_path):
    from scadview.docs_screenshots import ScreenshotManifestError, validate_manifest

    manifest_path = _write_valid_docs_tree(
        tmp_path,
        screenshots=[
            _screenshot_block("grid", "images/grid.png", "examples/sphere.py"),
            _screenshot_block("grid", "images/grid-again.png", "examples/sphere.py"),
        ],
        markdown_refs=["docs/images/grid.png", "docs/images/grid-again.png"],
    )

    with pytest.raises(ScreenshotManifestError, match="duplicate.*grid"):
        validate_manifest(manifest_path, repo_root=tmp_path)


def test_validate_manifest_ignores_markdown_outside_readme_and_docs(tmp_path):
    from scadview.docs_screenshots import ScreenshotManifestError, validate_manifest

    manifest_path = _write_valid_docs_tree(
        tmp_path,
        screenshots=[
            _screenshot_block("grid", "images/grid.png", "examples/sphere.py"),
        ],
        markdown_refs=[],
    )
    (tmp_path / "notes.md").write_text(
        "![Ignored](docs/images/grid.png)",
        encoding="utf-8",
    )

    with pytest.raises(ScreenshotManifestError, match="not referenced.*grid.png"):
        validate_manifest(manifest_path, repo_root=tmp_path)


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
        (
            [("grid", "images/grid.png", "examples/sphere.py", {})],
            [],
            None,
            "not referenced.*grid.png",
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
    from scadview.docs_screenshots import ScreenshotManifestError, validate_manifest

    screenshots = _screenshot_blocks(screenshot_specs)
    manifest_path = _write_valid_docs_tree(
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


def _screenshot_blocks(specs):
    if specs is None:
        return None
    return [
        _screenshot_block(name, output, module, **kwargs)
        for name, output, module, kwargs in specs
    ]


@pytest.mark.parametrize("view", ["frame", "xyz", "x", "y", "z"])
def test_validate_manifest_accepts_supported_view_values(tmp_path, view):
    from scadview.docs_screenshots import validate_manifest

    manifest_path = _write_valid_docs_tree(
        tmp_path,
        screenshots=[
            _screenshot_block(
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
    from scadview.docs_screenshots import validate_manifest

    manifest_path = _write_valid_docs_tree(
        tmp_path,
        screenshots=[
            _screenshot_block(
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


def test_docs_screenshots_task_runs_manifest_check_without_capture(monkeypatch):
    tasks = _load_tasks_module()

    commands = []
    monkeypatch.setattr(
        tasks,
        "_run_checked",
        lambda _context, command, **_kwargs: commands.append(command),
    )

    tasks.docs_screenshots.body(object(), args="grid sphere")

    assert commands == [
        "python -m scadview.docs_screenshots "
        "--manifest docs/screenshots.toml --check grid sphere"
    ]


def test_docs_screenshots_cli_check_returns_success(tmp_path):
    from scadview.docs_screenshots import main

    manifest_path = _write_valid_docs_tree(tmp_path)

    result = main(["--manifest", str(manifest_path), "--check", "grid"])

    assert result == 0


def test_generate_screenshots_delegates_validated_entries_to_capture_backend(tmp_path):
    from scadview.docs_screenshots import generate_screenshots, validate_manifest

    manifest_path = _write_valid_docs_tree(tmp_path)
    manifest = validate_manifest(
        manifest_path,
        repo_root=tmp_path,
        selected_names={"grid"},
    )
    backend = _RecordingCaptureBackend()

    generate_screenshots(manifest, repo_root=tmp_path, capture_backend=backend)

    assert backend.requests == [
        {
            "name": "grid",
            "module_path": tmp_path / "examples/sphere.py",
            "output_path": tmp_path / "docs/images/grid.png",
            "window_size": (960, 720),
            "view": "frame",
            "camera": "perspective",
            "grid": True,
            "axes": True,
            "edges": False,
            "gnomon": True,
        }
    ]


def test_docs_screenshots_cli_generation_uses_capture_backend_factory(tmp_path):
    import scadview.docs_screenshots as docs_screenshots

    manifest_path = _write_valid_docs_tree(tmp_path)
    backend = _RecordingCaptureBackend()

    result = docs_screenshots.main(
        ["--manifest", str(manifest_path), "sphere"],
        capture_backend_factory=lambda: backend,
    )

    assert result == 0
    assert [request["name"] for request in backend.requests] == ["sphere"]


def test_docs_screenshots_check_does_not_import_capture_backend(tmp_path, monkeypatch):
    import scadview.docs_screenshots as docs_screenshots

    manifest_path = _write_valid_docs_tree(tmp_path)
    monkeypatch.delitem(sys.modules, "scadview.ui.wx.docs_capture", raising=False)
    _fail_on_wx_import(monkeypatch)

    result = docs_screenshots.main(["--manifest", str(manifest_path), "--check"])

    assert result == 0
    assert "scadview.ui.wx.docs_capture" not in sys.modules


def test_mise_declares_docs_screenshots_task():
    payload = tomllib.loads(Path("mise.toml").read_text(encoding="utf-8"))

    task_config = payload["tasks"]["docs_screenshots"]

    assert task_config["description"] == "Validate docs screenshot manifest"
    assert task_config["depends"] == ["bootstrap_ci"]
    assert task_config["run"] == "uv run --no-sync inv docs_screenshots"


class _RecordingCaptureBackend:
    def __init__(self):
        self.requests = []

    def capture(self, request):
        self.requests.append(
            {
                "name": request.entry.name,
                "module_path": request.module_path,
                "output_path": request.output_path,
                "window_size": request.entry.window_size,
                "view": request.entry.view,
                "camera": request.entry.camera,
                "grid": request.entry.grid,
                "axes": request.entry.axes,
                "edges": request.entry.edges,
                "gnomon": request.entry.gnomon,
            }
        )


def _write_valid_docs_tree(
    tmp_path,
    *,
    screenshots=None,
    markdown_refs=None,
):
    docs_dir = tmp_path / "docs"
    examples_dir = tmp_path / "examples"
    docs_dir.mkdir()
    examples_dir.mkdir()
    (examples_dir / "sphere.py").write_text(
        "from trimesh.creation import icosphere\n\n"
        "def create_mesh():\n"
        "    return icosphere()\n",
        encoding="utf-8",
    )
    refs = markdown_refs
    if refs is None:
        refs = ["docs/images/grid.png", "docs/images/sphere.png"]
    _write_markdown_refs(tmp_path, refs)
    blocks = screenshots
    if blocks is None:
        blocks = [
            _screenshot_block("grid", "images/grid.png", "examples/sphere.py"),
            _screenshot_block("sphere", "images/sphere.png", "examples/sphere.py"),
        ]
    manifest_path = docs_dir / "screenshots.toml"
    manifest_path.write_text("\n".join(blocks), encoding="utf-8")
    return manifest_path


def _write_markdown_refs(tmp_path, refs):
    readme = tmp_path / "README.md"
    docs_examples = tmp_path / "docs" / "examples.md"
    readme.write_text(
        "\n".join(f"![Screenshot]({ref})" for ref in refs),
        encoding="utf-8",
    )
    docs_examples.write_text(
        "\n".join(f"![Screenshot]({ref.removeprefix('docs/')})" for ref in refs),
        encoding="utf-8",
    )


def _screenshot_block(
    name,
    output,
    module,
    *,
    view="frame",
    camera="perspective",
    window_size=None,
):
    size = window_size or [960, 720]
    return dedent(
        f"""
        [[screenshots]]
        name = "{name}"
        output = "{output}"
        module = "{module}"
        window_size = {_toml_list(size)}
        view = "{view}"
        camera = "{camera}"
        grid = true
        axes = true
        edges = false
        gnomon = true
        """
    ).strip()


def _toml_list(values):
    return "[" + ", ".join(_toml_value(value) for value in values) + "]"


def _toml_value(value):
    if isinstance(value, str):
        return f'"{value}"'
    return str(value)


def _fail_on_wx_import(monkeypatch):
    real_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "scadview.ui.wx" or name.startswith("scadview.ui.wx."):
            raise AssertionError(f"validation imported wx module {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)


def _load_tasks_module():
    spec = importlib.util.spec_from_file_location(
        "scadview_tasks_under_test",
        Path("tasks.py"),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
