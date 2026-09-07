from math import isclose

import pytest

from examples.stack_of_balls import create_mesh


def test_stack_of_balls_keeps_top_center_and_fixed_layer_spacing():
    meshes = create_mesh(
        levels=3,
        ball_radius=0.5,
        level_height=2.5,
        label="ignored",
        show_label=False,
    )

    centers = [mesh.center_mass for mesh in meshes]

    assert len(meshes) == 14
    assert all(isclose(value, 0.0, abs_tol=1e-9) for value in centers[0])
    assert isclose(abs(centers[1][0] - centers[2][0]), 2.0)
    assert isclose(abs(centers[1][1] - centers[3][1]), 2.0)
    assert isclose(centers[5][0] - centers[13][0], -4.0)
    assert isclose(centers[5][2], -5.0)

    larger_balls = create_mesh(
        levels=3,
        ball_radius=1.5,
        level_height=2.5,
        show_label=False,
    )
    larger_centers = [mesh.center_mass for mesh in larger_balls]
    assert isclose(larger_centers[5][0] - larger_centers[13][0], -4.0)


def test_stack_of_balls_uses_label_and_visibility_parameters():
    without_label = create_mesh(show_label=False)
    with_label = create_mesh(label="Demo", show_label=True)

    assert len(without_label) == 14
    assert len(with_label) == 15
    assert with_label[-1].vertices.shape[0] > 0


def test_stack_of_balls_label_is_above_top_ball_and_oriented_for_positive_x():
    meshes = create_mesh(
        levels=4,
        ball_radius=1.25,
        level_height=3.0,
        label="Demo",
        show_label=True,
    )
    top_ball = create_mesh(
        levels=4,
        ball_radius=1.25,
        level_height=3.0,
        show_label=False,
    )[0]
    label_mesh = meshes[-1]

    assert label_mesh.bounds[0][2] > top_ball.bounds[1][2]
    assert isclose(label_mesh.bounds[0][2] - top_ball.bounds[1][2], 0.25)
    assert label_mesh.face_normals[:, 0].max() > 0.99
    assert label_mesh.extents[1] > label_mesh.extents[2]


@pytest.mark.parametrize("levels", [0, -1])
def test_stack_of_balls_rejects_empty_stacks(levels):
    with pytest.raises(ValueError, match="levels"):
        create_mesh(levels=levels, show_label=False)
