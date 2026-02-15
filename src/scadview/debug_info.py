from __future__ import annotations

import json
import logging
import os
import platform
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import import_module, metadata
from pathlib import Path
from threading import Lock
from typing import Any, cast

logger = logging.getLogger(__name__)

DEFAULT_DEBUG_DIR_NAME = ".scadview"
DEFAULT_DEBUG_FILE_NAME = "debug_info.json"
DEFAULT_MAX_ARCHIVES = 5
REDACTED = "<redacted>"
REDACTED_PATH = "<redacted:path>"
ENV_DEBUG_INFO_FILE = "SCADVIEW_DEBUG_INFO_FILE"
ENV_DEBUG_INFO_REDACT_SENSITIVE = "SCADVIEW_DEBUG_INFO_REDACT_SENSITIVE"


def create_debug_info_service(
    scadview_args: list[str],
    output_file: str | None = None,
    redact_sensitive: bool | None = None,
) -> DebugInfoService:
    output_env = os.environ.get(ENV_DEBUG_INFO_FILE)
    output_path = (
        Path(output_file)
        if output_file
        else (Path(output_env) if output_env else _default_output_path())
    )
    effective_redact_sensitive = (
        _env_bool(ENV_DEBUG_INFO_REDACT_SENSITIVE, True)
        if redact_sensitive is None
        else redact_sensitive
    )
    settings = DebugInfoSettings(
        scadview_args=scadview_args,
        output_path=output_path,
        redact_sensitive=effective_redact_sensitive,
        redact_paths=effective_redact_sensitive,
    )
    return DebugInfoService(settings)


@dataclass(frozen=True)
class DebugInfoSettings:
    scadview_args: list[str]
    output_path: Path
    redact_sensitive: bool = True
    redact_paths: bool = True


class DebugInfoService:
    def __init__(self, settings: DebugInfoSettings):
        self._settings = settings
        self._output_path = settings.output_path
        redaction_settings = _RedactionSettings(
            redact_sensitive=settings.redact_sensitive,
            redact_paths=settings.redact_paths,
        )
        self._lock = Lock()

        _rotate_debug_info_files(self._output_path, DEFAULT_MAX_ARCHIVES)
        self._recorder = DebugInfoRecorder(self._output_path)
        self._recorder.update_section(
            "python_runtime", _capture_python_runtime(redaction_settings)
        )
        self._recorder.update_section("os_hardware", _capture_os_hardware())
        self._recorder.update_section(
            "critical_library_versions", _capture_critical_library_versions()
        )
        self._recorder.update_section(
            "execution_context",
            _capture_execution_context(
                settings.scadview_args, self._output_path, redaction_settings
            ),
        )
        self._recorder.update_section(
            "user_configuration", _capture_user_configuration(redaction_settings)
        )
        self._recorder.update_section(
            "gui_toolkit", _capture_gui_toolkit(include_screens=False)
        )

    @property
    def output_path(self) -> Path:
        return self._output_path

    def capture_gpu_opengl_stack(self, context: Any):
        with self._lock:
            info = getattr(context, "info", {})
            vendor = _info_lookup(info, "GL_VENDOR", "VENDOR")
            renderer = _info_lookup(info, "GL_RENDERER", "RENDERER")
            version = _info_lookup(info, "GL_VERSION", "VERSION")
            glsl = _info_lookup(
                info,
                "GL_SHADING_LANGUAGE_VERSION",
                "SHADING_LANGUAGE_VERSION",
                "GLSL_VERSION",
            )
            payload = {
                "context_version_code": getattr(context, "version_code", None),
                "context_vendor": getattr(context, "vendor", None) or vendor,
                "context_renderer": getattr(context, "renderer", None) or renderer,
                "context_version": getattr(context, "version", None) or version,
                "context_info": info,
                "opengl_vendor": vendor,
                "opengl_renderer": renderer,
                "opengl_version": version,
                "glsl_version": glsl,
            }
            self._recorder.update_section("gpu_opengl_stack", payload)

    def capture_gui_toolkit(self):
        with self._lock:
            self._recorder.update_section("gui_toolkit", _capture_gui_toolkit())


def _default_output_path() -> Path:
    return Path.cwd() / DEFAULT_DEBUG_DIR_NAME / DEFAULT_DEBUG_FILE_NAME


def _rotate_debug_info_files(path: Path, max_archives: int):
    if max_archives <= 0:
        return

    oldest = _archived_path(path, max_archives)
    if oldest.exists():
        oldest.unlink()

    for i in range(max_archives - 1, 0, -1):
        src = _archived_path(path, i)
        dst = _archived_path(path, i + 1)
        if src.exists():
            src.replace(dst)

    if path.exists():
        path.replace(_archived_path(path, 1))


def _archived_path(path: Path, index: int) -> Path:
    return path.with_name(f"{path.stem}.{index}{path.suffix}")


class DebugInfoRecorder:
    def __init__(self, path: Path):
        self.path = path
        self._data: dict[str, Any] = {}
        self._write_lock = Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._write()
        logger.info(f"Debug info output file: {self.path}")
        logger.warning(f"Debug info file: {self.path}")

    def update_section(self, section: str, payload: dict[str, Any]):
        with self._write_lock:
            self._data[section] = _to_jsonable(payload)
            self._write()
        logger.info(f"Captured debug info section '{section}'")

    def _write(self):
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, sort_keys=True)
            f.write("\n")


class _RedactionSettings:
    def __init__(self, redact_sensitive: bool, redact_paths: bool):
        self.redact_sensitive = redact_sensitive
        self.redact_paths = redact_paths


def _capture_python_runtime(settings: _RedactionSettings) -> dict[str, Any]:
    tcltk = _capture_tcltk_runtime()
    return {
        "version": sys.version,
        "implementation": platform.python_implementation(),
        "compiler": platform.python_compiler(),
        "executable": _redact_path(sys.executable, settings.redact_paths),
        "tcltk": tcltk,
    }


def _capture_tcltk_runtime() -> dict[str, Any]:
    try:
        import tkinter

        return {
            "included": True,
            "tcl_version": str(getattr(tkinter, "TclVersion", "")),
            "tk_version": str(getattr(tkinter, "TkVersion", "")),
        }
    except Exception as e:
        return {
            "included": False,
            "error": str(e),
        }


def _capture_os_hardware() -> dict[str, Any]:
    return {
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "architecture": platform.architecture(),
        "cpu_count": os.cpu_count(),
    }


def _capture_critical_library_versions() -> dict[str, str | None]:
    return {
        "scadview": _safe_version("scadview"),
        "numpy": _safe_version("numpy"),
        "moderngl": _safe_version("moderngl"),
        "trimesh": _safe_version("trimesh"),
        "wxpython": _safe_version("wxpython"),
        "pyrr": _safe_version("pyrr"),
        "scipy": _safe_version("scipy"),
        "shapely": _safe_version("shapely"),
        "manifold3d": _safe_version("manifold3d"),
        "matplotlib": _safe_version("matplotlib"),
        "pillow": _safe_version("pillow"),
    }


def _safe_version(package_name: str) -> str | None:
    try:
        return metadata.version(package_name)
    except metadata.PackageNotFoundError:
        return None


def _capture_execution_context(
    cli_args: list[str], output_path: Path, settings: _RedactionSettings
) -> dict[str, Any]:
    pid = REDACTED if settings.redact_sensitive else os.getpid()
    ppid = REDACTED if settings.redact_sensitive else os.getppid()
    return {
        "utc_now": datetime.now(timezone.utc).isoformat(),
        "argv": _redact_args(sys.argv, settings),
        "scadview_cli_arguments": _redact_args(cli_args, settings),
        "debug_info_file": _redact_path(str(output_path), settings.redact_paths),
        "cwd": _redact_path(os.getcwd(), settings.redact_paths),
        "pid": pid,
        "ppid": ppid,
    }


def _capture_user_configuration(settings: _RedactionSettings) -> dict[str, Any]:
    scadview_env = {
        key: value for key, value in os.environ.items() if key.startswith("SCADVIEW_")
    }
    if settings.redact_sensitive:
        scadview_env = {key: REDACTED for key in scadview_env.keys()}
    return {
        "home": _redact_path(os.path.expanduser("~"), settings.redact_paths),
        "config_override_file": _redact_path(
            os.environ.get(ENV_DEBUG_INFO_FILE), settings.redact_paths
        ),
        "scadview_environment_variables": scadview_env,
        "virtual_env": _redact_path(
            os.environ.get("VIRTUAL_ENV"), settings.redact_paths
        ),
        "pythonpath": _redact_path(os.environ.get("PYTHONPATH"), settings.redact_paths),
    }


def _capture_gui_toolkit(include_screens: bool = True) -> dict[str, Any]:
    try:
        wx = cast(
            Any, import_module("wx")
        )  # Avoids errors in the CI which does not install wx

        payload: dict[str, Any] = {
            "toolkit": "wxPython",
            "version": wx.version(),
            "platform_info": list(wx.PlatformInfo),
        }
        if include_screens:
            screens, screen_capture_error, app_initialized = _capture_screens(wx)
            payload["screens"] = screens
            payload["wx_app_initialized"] = app_initialized
            if screen_capture_error is not None:
                payload["screen_capture_error"] = screen_capture_error
        return payload
    except Exception as e:
        return {"toolkit": "wxPython", "error": str(e)}


def _capture_screens(wx: Any) -> tuple[list[dict[str, Any]], str | None, bool]:
    app = wx.App.Get()
    if app is None:
        return [], "wx.App is not initialized yet", False

    screens: list[dict[str, Any]] = []
    try:
        display_count = int(wx.Display.GetCount())
        for idx in range(display_count):
            display = wx.Display(idx)
            geometry = display.GetGeometry()
            entry: dict[str, Any] = {
                "index": idx,
                "x": int(geometry.x),
                "y": int(geometry.y),
                "width": int(geometry.width),
                "height": int(geometry.height),
            }
            try:
                entry["scale_factor"] = float(display.GetScaleFactor())
            except Exception:
                # Not all wx backends expose this; keep capture best-effort.
                entry["scale_factor"] = None
            screens.append(entry)
        return screens, None, True
    except Exception as e:
        return [], str(e), True


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        obj = cast(dict[object, Any], value)
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(value, (list, tuple)):
        seq = cast(list[Any] | tuple[Any, ...], value)
        return [_to_jsonable(v) for v in seq]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _info_lookup(info: Any, *keys: str) -> Any:
    if not isinstance(info, dict):
        return None

    info_dict = cast(dict[object, Any], info)
    string_keyed: dict[str, Any] = {str(k): v for k, v in info_dict.items()}

    for key in keys:
        if key in string_keyed:
            return string_keyed[key]

    upper_keys: dict[str, str] = {k.upper(): k for k in string_keyed.keys()}
    for key in keys:
        mapped = upper_keys.get(key.upper())
        if mapped is not None:
            return string_keyed[mapped]
    return None


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return default


def _redact_path(value: str | None, redact_paths: bool) -> str | None:
    if value is None or not redact_paths:
        return value
    return REDACTED_PATH


def _redact_args(values: list[str], settings: _RedactionSettings) -> list[str]:
    if not settings.redact_sensitive:
        return values
    redacted: list[str] = []
    for value in values:
        if settings.redact_paths and (_looks_like_path(value) or os.sep in value):
            redacted.append(REDACTED_PATH)
        else:
            redacted.append(value)
    return redacted


def _looks_like_path(value: str) -> bool:
    if value.startswith(("~", "/", "./", "../")):
        return True
    if len(value) >= 3 and value[1:3] == ":\\":
        return True
    return False
