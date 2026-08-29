from pathlib import Path


def test_feature_example_and_docs_explain_debug_features():
    example = Path("examples/features.py").read_text(encoding="utf-8")
    examples_docs = Path("docs/examples.md").read_text(encoding="utf-8")
    ui_docs = Path("docs/user_interface.md").read_text(encoding="utf-8")

    assert "Debug features" in example
    assert "Debug features" in examples_docs
    assert "cable_cutout" in examples_docs
    assert "Debug features" in ui_docs
    assert "enabled" in ui_docs
