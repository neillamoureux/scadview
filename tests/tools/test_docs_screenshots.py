import sys
import tomllib
from pathlib import Path

from tests.tools.docs_screenshots_test_support import write_valid_docs_tree


def test_tools_package_exposes_docs_screenshots_module():
    import tools.docs_screenshots as docs_screenshots

    assert docs_screenshots.__name__ == "tools.docs_screenshots"


def test_runtime_package_does_not_contain_docs_screenshot_tooling():
    forbidden_paths = [
        Path("src/scadview/docs_screenshots.py"),
        Path("src/scadview/ui/wx/docs_capture.py"),
    ]

    assert [path for path in forbidden_paths if path.exists()] == []


def test_runtime_package_does_not_import_tools_package():
    runtime_imports = []
    for path in Path("src/scadview").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "from tools" in text or "import tools" in text:
            runtime_imports.append(path)

    assert runtime_imports == []


def test_main_frame_does_not_expose_docs_specific_hooks():
    main_frame_source = Path("src/scadview/ui/wx/main_frame.py").read_text(
        encoding="utf-8"
    )

    assert "docs_screenshot" not in main_frame_source
    assert "ScreenshotEntry" not in main_frame_source


def test_gl_widget_does_not_import_moderngl():
    gl_widget_source = Path("src/scadview/ui/wx/gl_widget.py").read_text(
        encoding="utf-8"
    )

    assert "moderngl" not in gl_widget_source


def test_docs_screenshots_cli_defaults_to_validation(tmp_path):
    from tools.docs_screenshots import main

    manifest_path = write_valid_docs_tree(tmp_path)

    result = main(["--manifest", str(manifest_path), "grid"])

    assert result == 0


def test_docs_screenshots_validation_does_not_import_capture_backend(
    tmp_path, monkeypatch
):
    import tools.docs_screenshots as docs_screenshots

    manifest_path = write_valid_docs_tree(tmp_path)
    monkeypatch.delitem(sys.modules, "tools.docs_screenshots_generate", raising=False)
    monkeypatch.delitem(sys.modules, "scadview.ui.wx", raising=False)
    monkeypatch.delitem(sys.modules, "scadview.ui.wx.main_frame", raising=False)
    from tests.tools.docs_screenshots_test_support import fail_on_wx_import

    fail_on_wx_import(monkeypatch)

    result = docs_screenshots.main(["--manifest", str(manifest_path)])

    assert result == 0
    assert "tools.docs_screenshots_generate" not in sys.modules
    assert "scadview.ui.wx.main_frame" not in sys.modules


def test_mise_declares_docs_screenshot_tasks():
    payload = tomllib.loads(Path("mise.toml").read_text(encoding="utf-8"))

    assert "docs_screenshots" not in payload["tasks"]

    check_task = payload["tasks"]["docs_check_screenshots_manifest"]
    assert check_task["description"] == "Validate docs screenshot manifest"
    assert check_task["depends"] == ["bootstrap"]
    assert check_task["run"] == _docs_screenshots_command()

    generate_task = payload["tasks"]["docs_generate_screenshots"]
    assert generate_task["description"] == "Generate docs screenshots"
    assert generate_task["depends"] == ["bootstrap"]
    assert generate_task["run"] == f"{_docs_screenshots_command()} --generate"


def _docs_screenshots_command() -> str:
    return (
        'PYTHONPATH="$PWD:$PWD/src${PYTHONPATH:+:$PYTHONPATH}" '
        "uv run --no-sync python -m tools.docs_screenshots "
        "--manifest docs/screenshots.toml"
    )
