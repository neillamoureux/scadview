from pathlib import Path


def test_feature_example_and_docs_explain_debug_features():
    example = Path("examples/features.py").read_text(encoding="utf-8")
    examples_docs = Path("docs/examples.md").read_text(encoding="utf-8")
    ui_docs = Path("docs/user_interface.md").read_text(encoding="utf-8")
    create_mesh_docs = Path("docs/create_mesh.md").read_text(encoding="utf-8")
    screenshot_manifest = Path("docs/screenshots.toml").read_text(encoding="utf-8")

    assert "ordinary enabled/disabled" in example
    assert "### Feature controls" in examples_docs
    assert "![Features](images/features.png)" in examples_docs
    assert "Debug features" in example
    assert "### Debug features" in examples_docs
    assert "![Debug features](images/features_debug.png)" in examples_docs
    assert Path("docs/images/features_debug.png").is_file()
    assert "cable_cutout" in examples_docs
    assert "Unregistered meshes" in examples_docs
    assert "Debug features" in ui_docs
    assert "enabled" in ui_docs
    assert "Unregistered" in ui_docs
    assert "Debug features" in create_mesh_docs
    assert "not marked as features" in create_mesh_docs
    assert "# [[screenshots]]" in screenshot_manifest
    assert '# name = "features_debug"' in screenshot_manifest
    assert "issue #161" in screenshot_manifest
