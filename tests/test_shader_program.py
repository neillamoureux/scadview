import pytest
from unittest.mock import MagicMock, patch
from meshsee.shader_program import ShaderProgram, ShaderVar
from meshsee.observable import Observable


@pytest.fixture
def mock_context():
    return MagicMock()


@pytest.fixture
def shader_program(mock_context):
    register = {
        # ShaderVar.MODEL_MATRIX: "u_modelMatrix",
        ShaderVar.VIEW_MATRIX: "u_viewMatrix",
        ShaderVar.PROJECTION_MATRIX: "u_projectionMatrix",
        ShaderVar.MESH_COLOR: "u_meshColor",
        ShaderVar.SHOW_GRID: "u_showGrid",
    }
    with (
        patch("meshsee.shader_program.as_file") as mock_as_file,
        patch("meshsee.shader_program.moderngl.Uniform") as Uniform,
    ):
        mock_as_file.return_value.__enter__.return_value.read_text.return_value = (
            "shader code"
        )
        return ShaderProgram(
            ctx=mock_context,
            vertex_shader_loc="vertex_shader.glsl",
            fragment_shader_loc="fragment_shader.glsl",
            register=register,
        )


def test_shader_program_initialization(shader_program, mock_context):
    assert shader_program._ctx == mock_context
    assert isinstance(shader_program.register, dict)
    assert shader_program.program is not None


def test_update_program_var_boolean(shader_program):
    mock_uniform = MagicMock()
    mock_uniform.gl_type = ShaderProgram.BOOLEAN
    shader_program.program = {"u_showGrid": mock_uniform}

    shader_program.update_program_var(ShaderVar.SHOW_GRID, True)
    mock_uniform.value = True
    mock_uniform.write.assert_not_called()


def test_update_program_var_non_boolean(shader_program):
    mock_uniform = MagicMock()
    mock_uniform.gl_type = "non_boolean_type"
    shader_program.program = {"u_meshColor": mock_uniform}

    shader_program.update_program_var(ShaderVar.MESH_COLOR, b"color_data")
    mock_uniform.write.assert_called_once_with(b"color_data")


def test_update_program_var_invalid_var(shader_program):
    shader_program.update_program_var(ShaderVar.MODEL_MATRIX, b"data")
    # No exception should be raised for invalid vars


def test_subscribe_to_updates(shader_program):
    mock_observable = MagicMock(spec=Observable)
    shader_program.subscribe_to_updates(mock_observable)
    mock_observable.subscribe.assert_called_once_with(shader_program.update_program_var)
