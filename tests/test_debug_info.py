import json
import logging
import os
from pathlib import Path

from scadview.debug_info import (
    DEFAULT_DEBUG_DIR_NAME,
    DEFAULT_DEBUG_FILE_NAME,
    REDACTED,
    REDACTED_PATH,
    DebugInfoService,
    DebugInfoSettings,
    _capture_screens,
    create_debug_info_service,
)


def _make_service(
    tmp_path,
    *,
    scadview_args: list[str] | None = None,
    redact_sensitive: bool = False,
    redact_paths: bool = False,
) -> tuple[DebugInfoService, Path]:
    output_file = tmp_path / "debug_info.json"
    settings = DebugInfoSettings(
        scadview_args=scadview_args or [],
        output_path=output_file,
        redact_sensitive=redact_sensitive,
        redact_paths=redact_paths,
    )
    return DebugInfoService(settings), output_file


def test_debug_info_service_writes_expected_sections(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    service, output_file = _make_service(
        tmp_path,
        scadview_args=["-v", "--foo=bar"],
        redact_sensitive=False,
        redact_paths=False,
    )
    path = service.output_path

    assert path == output_file
    assert output_file.exists()

    with output_file.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    for key in [
        "python_runtime",
        "os_hardware",
        "critical_library_versions",
        "execution_context",
        "user_configuration",
        "gui_toolkit",
    ]:
        assert key in payload
    assert "included" in payload["python_runtime"]["tcltk"]
    assert isinstance(payload["python_runtime"]["tcltk"]["included"], bool)

    assert payload["execution_context"]["scadview_cli_arguments"] == ["-v", "--foo=bar"]
    assert payload["execution_context"]["debug_info_file"] == str(output_file)
    assert isinstance(payload["execution_context"]["pid"], int)
    assert isinstance(payload["execution_context"]["ppid"], int)
    assert "Captured debug info section 'python_runtime'" in caplog.text
    assert f"Debug info file: {output_file}" in caplog.text


def test_capture_gpu_opengl_stack_adds_section(tmp_path):
    service, output_file = _make_service(tmp_path)

    class _FakeContext:
        version_code = 460
        vendor = "Fake Vendor"
        renderer = "Fake Renderer"
        version = "4.6"
        info = {
            "GL_VENDOR": "Fake Vendor",
            "GL_RENDERER": "Fake Renderer",
            "GL_VERSION": "4.6",
            "GL_SHADING_LANGUAGE_VERSION": "4.60",
        }

    service.capture_gpu_opengl_stack(_FakeContext())

    with output_file.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    assert payload["gpu_opengl_stack"]["context_version_code"] == 460
    assert payload["gpu_opengl_stack"]["opengl_vendor"] == "Fake Vendor"


def test_capture_gpu_opengl_stack_uses_alternate_info_keys(tmp_path):
    service, output_file = _make_service(tmp_path)

    class _FakeContext:
        version_code = 410
        vendor = None
        renderer = None
        version = None
        info = {
            "vendor": "Alt Vendor",
            "renderer": "Alt Renderer",
            "version": "4.1",
            "shading_language_version": "4.10",
        }

    service.capture_gpu_opengl_stack(_FakeContext())

    with output_file.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    gpu = payload["gpu_opengl_stack"]
    assert gpu["context_version_code"] == 410
    assert gpu["context_vendor"] == "Alt Vendor"
    assert gpu["context_renderer"] == "Alt Renderer"
    assert gpu["context_version"] == "4.1"
    assert gpu["glsl_version"] == "4.10"


def test_create_debug_info_service_defaults_to_dot_scadview_dir(tmp_path, monkeypatch):
    monkeypatch.delenv("SCADVIEW_DEBUG_INFO_FILE", raising=False)
    monkeypatch.setenv("SCADVIEW_DEBUG_INFO_REDACT_SENSITIVE", "false")
    monkeypatch.chdir(tmp_path)

    path = create_debug_info_service([]).output_path

    assert path == tmp_path / DEFAULT_DEBUG_DIR_NAME / DEFAULT_DEBUG_FILE_NAME
    assert path.exists()


def test_create_debug_info_service_rotates_previous_file(tmp_path, monkeypatch):
    monkeypatch.delenv("SCADVIEW_DEBUG_INFO_FILE", raising=False)
    monkeypatch.setenv("SCADVIEW_DEBUG_INFO_REDACT_SENSITIVE", "false")
    monkeypatch.chdir(tmp_path)
    debug_dir = tmp_path / DEFAULT_DEBUG_DIR_NAME
    debug_dir.mkdir(parents=True, exist_ok=True)
    current = debug_dir / DEFAULT_DEBUG_FILE_NAME
    current.write_text('{"old": true}\n', encoding="utf-8")

    path = create_debug_info_service([]).output_path
    archive_1 = debug_dir / "debug_info.1.json"

    assert path == current
    assert archive_1.exists()
    assert json.loads(archive_1.read_text(encoding="utf-8")) == {"old": True}


def test_create_debug_info_service_redacts_paths_by_default(tmp_path, monkeypatch):
    output_file = tmp_path / "debug_info.json"
    monkeypatch.setenv("SCADVIEW_DEBUG_INFO_FILE", str(output_file))
    monkeypatch.delenv("SCADVIEW_DEBUG_INFO_REDACT_SENSITIVE", raising=False)

    create_debug_info_service([])
    with output_file.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    assert payload["execution_context"]["debug_info_file"] == REDACTED_PATH
    assert payload["execution_context"]["cwd"] == REDACTED_PATH
    assert payload["execution_context"]["pid"] == REDACTED
    assert payload["execution_context"]["ppid"] == REDACTED
    assert payload["python_runtime"]["executable"] == REDACTED_PATH
    assert payload["user_configuration"]["pythonpath"] in (None, REDACTED_PATH)
    assert payload["user_configuration"]["virtual_env"] in (None, REDACTED_PATH)


def test_create_debug_info_service_uses_env_to_disable_redaction(tmp_path, monkeypatch):
    output_file = tmp_path / "debug_info.json"
    monkeypatch.setenv("SCADVIEW_DEBUG_INFO_FILE", str(output_file))
    monkeypatch.setenv("SCADVIEW_DEBUG_INFO_REDACT_SENSITIVE", "false")

    create_debug_info_service([])
    with output_file.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    assert payload["execution_context"]["debug_info_file"] == str(output_file)
    assert payload["execution_context"]["cwd"] == os.getcwd()
    assert isinstance(payload["execution_context"]["pid"], int)
    assert isinstance(payload["execution_context"]["ppid"], int)


def test_capture_screens_returns_soft_error_when_no_wx_app():
    class _FakeApp:
        @staticmethod
        def Get():
            return None

    class _FakeWx:
        App = _FakeApp

    screens, error, app_initialized = _capture_screens(_FakeWx)

    assert screens == []
    assert error == "wx.App is not initialized yet"
    assert app_initialized is False


def test_capture_screens_returns_dimensions_and_scale():
    class _Geometry:
        x = 10
        y = 20
        width = 1920
        height = 1080

    class _Display:
        @staticmethod
        def GetCount():
            return 1

        def __init__(self, idx):
            assert idx == 0

        def GetGeometry(self):
            return _Geometry()

        def GetScaleFactor(self):
            return 2.0

    class _FakeApp:
        @staticmethod
        def Get():
            return object()

    class _FakeWx:
        App = _FakeApp
        Display = _Display

    screens, error, app_initialized = _capture_screens(_FakeWx)

    assert app_initialized is True
    assert error is None
    assert screens == [
        {
            "index": 0,
            "x": 10,
            "y": 20,
            "width": 1920,
            "height": 1080,
            "scale_factor": 2.0,
        }
    ]
