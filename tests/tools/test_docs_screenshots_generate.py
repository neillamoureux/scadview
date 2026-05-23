from tests.tools.docs_screenshots_test_support import (
    RecordingCaptureBackend,
    write_valid_docs_tree,
)


def test_tools_package_exposes_docs_screenshots_generate_module():
    import tools.docs_screenshots_generate as docs_screenshots_generate

    assert docs_screenshots_generate.__name__ == "tools.docs_screenshots_generate"


def test_generate_screenshots_delegates_validated_entries_to_capture_backend(tmp_path):
    from tools.docs_screenshots import generate_screenshots
    from tools.docs_screenshots_check import validate_manifest

    manifest_path = write_valid_docs_tree(tmp_path)
    manifest = validate_manifest(
        manifest_path,
        repo_root=tmp_path,
        selected_names={"grid"},
    )
    backend = RecordingCaptureBackend()

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
    import tools.docs_screenshots as docs_screenshots

    manifest_path = write_valid_docs_tree(tmp_path)
    backend = RecordingCaptureBackend()

    result = docs_screenshots.main(
        ["--manifest", str(manifest_path), "--generate", "sphere"],
        capture_backend_factory=lambda: backend,
    )

    assert result == 0
    assert [request["name"] for request in backend.requests] == ["sphere"]
