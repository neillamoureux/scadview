import builtins
from pathlib import Path
from textwrap import dedent


def screenshot_blocks(specs):
    if specs is None:
        return None
    return [
        screenshot_block(name, output, module, **kwargs)
        for name, output, module, kwargs in specs
    ]


def write_valid_docs_tree(
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
    write_markdown_refs(tmp_path, refs)
    blocks = screenshots
    if blocks is None:
        blocks = [
            screenshot_block("grid", "images/grid.png", "examples/sphere.py"),
            screenshot_block("sphere", "images/sphere.png", "examples/sphere.py"),
        ]
    manifest_path = docs_dir / "screenshots.toml"
    manifest_path.write_text("\n".join(blocks), encoding="utf-8")
    return manifest_path


def write_markdown_refs(tmp_path, refs):
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


def screenshot_block(
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
        window_size = {toml_list(size)}
        view = "{view}"
        camera = "{camera}"
        grid = true
        axes = true
        edges = false
        gnomon = true
        """
    ).strip()


def toml_list(values):
    return "[" + ", ".join(toml_value(value) for value in values) + "]"


def toml_value(value):
    if isinstance(value, str):
        return f'"{value}"'
    return str(value)


def fail_on_wx_import(monkeypatch):
    real_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "scadview.ui.wx" or name.startswith("scadview.ui.wx."):
            raise AssertionError(f"validation imported wx module {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)


class RecordingCaptureBackend:
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
