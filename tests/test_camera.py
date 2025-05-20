from copy import copy, deepcopy
from math import acos, cos

from pytest import approx, mark
import numpy as np

from meshsee.camera import Camera, intersection


def test_intersection():
    range1 = (0, 1)
    range2 = (0.5, 1.5)
    actual = intersection(range1, range2)
    expected = (0.5, 1)
    assert actual == expected
    range2 = (0, 1)
    actual = intersection(range1, range2)
    expected = (0, 1)
    assert actual == expected
    range2 = (1, 2)
    actual = intersection(range1, range2)
    expected = (1, 1)
    assert actual == expected
    range2 = (2, 3)
    actual = intersection(range1, range2)
    expected = None
    assert actual == expected
    range2 = (0.5, 0.5)
    actual = intersection(range1, range2)
    expected = (0.5, 0.5)
    assert actual == expected
    range2 = (-0.5, 0.5)
    actual = intersection(range1, range2)
    expected = (0, 0.5)
    assert actual == expected
    range2 = (-0.5, -0.1)
    actual = intersection(range1, range2)
    expected = None
    assert actual == expected


def test_intersection_inf():
    range1 = (0, np.inf)
    range2 = (-np.inf, 0.5)
    actual = intersection(range1, range2)
    expected = (0, 0.5)
    assert actual == expected
    range2 = (0.5, np.inf)
    actual = intersection(range1, range2)
    expected = (0.5, np.inf)
    assert actual == expected


def test_intersection_none():
    range1 = (0, 1)
    range2 = None
    actual = intersection(range1, range2)
    expected = None
    assert actual == expected
    actual = intersection(range2, range1)
    assert actual == expected


def test_init():
    cam = Camera()
    assert np.array_equal(cam.position, Camera.POSITION_INIT)
    assert np.array_equal(cam.look_at, Camera.LOOK_AT_INIT)
    assert np.array_equal(cam.up, Camera.Z_DIR)
    assert cam.fovy == Camera.FOVY_INIT
    assert cam.aspect_ratio == 1.0
    assert cam.near == Camera.NEAR_INIT
    assert cam.far == Camera.FAR_INIT


def test_position():
    cam = Camera()
    cam.position = np.array([1.0, 2.0, 3.0])
    assert np.array_equal(cam.position, np.array([1.0, 2.0, 3.0]))


def test_look_at():
    cam = Camera()
    cam.look_at = np.array([1.0, 2.0, 3.0])
    assert np.array_equal(cam.look_at, np.array([1.0, 2.0, 3.0]))


def test_up():
    cam = Camera()
    cam.up = np.array([1.0, 2.0, 3.0])
    assert np.array_equal(cam.up, np.array([1.0, 2.0, 3.0]))


def test_fovy():
    cam = Camera()
    cam.fovy = 45.0
    assert cam.fovy == 45.0


def test_aspect_ratio():
    cam = Camera()
    cam.aspect_ratio = 1.5
    assert cam.aspect_ratio == 1.5


def test_near():
    cam = Camera()
    cam.near = 0.5
    assert cam.near == 0.5


def test_far():
    cam = Camera()
    cam.far = 100.0
    assert cam.far == 100.0


def test_direction():
    cam = Camera()
    cam.position = np.array([1.0, 2.0, 3.0])
    cam.look_at = np.array([-1.0, -2.0, -3.0])
    assert np.array_equal(cam.direction, np.array([-2.0, -4.0, -6.0]))


def test_perpendicular_up():
    cam = Camera()
    perpendicular_up = cam.perpendicular_up
    approx(np.linalg.norm(perpendicular_up), 1e-6)
    approx(np.dot(cam.direction, perpendicular_up), 1e-6)


def test_view_matrix():
    cam = Camera()
    cam.position = np.array([1.0, 2.0, 3.0])
    cam.look_at = np.array([0.0, 0.0, 0.0])
    cam.up = np.array([0.0, 1.0, 0.0])
    view_matrix = cam.view_matrix
    assert view_matrix.shape == (4, 4)
    approx(
        view_matrix,
        np.array(
            [
                [-0.9486833, 0.0, 0.3162278, 0.0],
                [-0.3162278, 0.0, -0.9486833, 0.0],
                [0.0, -1.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ]
        ),
    )


def test_view_matrix2():
    cam = Camera()
    cam.position = np.array([1.0, 2.0, 3.0])
    cam.look_at = np.array([-1.0, -2.0, -3.0])
    cam.up = np.array([1.0, 1.0, 0.0])
    view_matrix = cam.view_matrix
    assert view_matrix.shape == (4, 4)
    assert view_matrix.dtype == np.float32

    # Look at should map to [0, 0, -distance] in camera space
    vm_dot_look_at = view_matrix.T.dot(np.append(cam.look_at, 1.0))
    distance = np.linalg.norm(cam.look_at - cam.position)
    assert vm_dot_look_at[0:3] / vm_dot_look_at[3] == approx(
        np.array([0.0, 0.0, -distance]), abs=1e-6
    )

    # Perp up  starting from position should map to [0, 1, 0] in camera space
    vm_dot_up = view_matrix.T.dot(np.append(cam.perpendicular_up + cam.position, 1.0))
    assert vm_dot_up[0:3] / vm_dot_up[3] == approx(np.array([0.0, 1.0, 0.0]), abs=1e-6)

    # Position should map to [0, 0, 0] in camera space
    vm_dot_position = view_matrix.T.dot(np.append(cam.position, 1.0))
    assert vm_dot_position[0:3] / vm_dot_position[3] == approx(
        np.array([0.0, 0.0, 0.0]), abs=1e-6
    )

    # Normalized direction should map to [0, 0, -1] in camera space
    norm_direction = cam.direction / np.linalg.norm(cam.direction)
    vm_dot_norm_direction = view_matrix.T.dot(
        np.append(norm_direction + cam.position, 1.0)
    )
    assert vm_dot_norm_direction[0:3] / vm_dot_norm_direction[3] == approx(
        np.array([0.0, 0.0, -1.0]), abs=1e-6
    )


def test_projection_matrix():
    cam = Camera()
    cam.aspect_ratio = 2.0
    cam.fovy = 90.0
    cam.near = 1.0
    cam.far = 100.0
    projection_matrix = cam.projection_matrix
    assert projection_matrix.shape == (4, 4)
    assert projection_matrix.dtype == np.float32
    approx(
        projection_matrix,
        np.array(
            [
                [0.5, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, -1.020202, -2.020202],
                [0.0, 0.0, -1.0, 0.0],
            ]
        ),
    )


def test_projection_matrix_near_and_far():
    # Note: OpenGL is right-handed, so the z-axis is pointing out of the screen back to the viewer
    cam = Camera()
    cam.aspect_ratio = 2.0
    cam.fovy = 45.0
    cam.near = 0.25
    cam.far = 100.0
    cam.look_at = np.array([0.0, 0.0, 1.0])
    cam.up = np.array([0.0, 1.0, 0.0])
    cam.position = np.array([0.0, 0.0, 0.0])
    projection_matrix = cam.projection_matrix
    assert projection_matrix.shape == (4, 4)
    # near should map to [0, 0, 1] in clip space, or in 4 dim [0, 0, z, -z], z arbitrary
    near_product = projection_matrix.T.dot(
        cam.view_matrix.T.dot(np.array([0.0, 0.0, cam.near, 1.0]))
    )
    assert near_product[0:2] == approx(np.array([0.0, 0.0]))
    assert near_product[2] == approx(-near_product[3])
    # far should map to [0, 0, -1] in clip space, or in 4 dim [0, 0, z, z], z arbitrary
    far_product = projection_matrix.T.dot(
        cam.view_matrix.T.dot(np.array([0.0, 0.0, cam.far, 1.0]))
    )
    assert far_product[0:2] == approx(np.array([0.0, 0.0]))
    # assert far_product[2] / far_product[3] == approx(-1.0)
    assert far_product[2] == approx(far_product[3])


# test fov by placing at corner of near plane
def test_projection_matrix_fov():
    # Note: OpenGL is right-handed, so the z-axis is pointing out of the screen back to the viewer
    cam = Camera()
    cam.aspect_ratio = 2.0
    cam.fovy = 53.0
    cam.near = 0.02
    cam.far = 100.0
    cam.look_at = np.array([0.0, 0.0, 1.0])
    cam.up = np.array([0.0, 1.0, 0.0])
    cam.position = np.array([0.0, 0.0, 0.0])
    projection_matrix = cam.projection_matrix
    assert projection_matrix.shape == (4, 4)
    y = cam.near * np.tan(np.radians(cam.fovy) / 2)
    x = -y * cam.aspect_ratio
    near_product = projection_matrix.T.dot(
        cam.view_matrix.T.dot(np.array([x, y, cam.near, 1.0]))
    )
    # Not sure about the signs, esp why z = -1.
    assert near_product[0:3] / near_product[3] == approx(np.array([1.0, 1.0, -1.0]))


def test_orbit_look_at_unchanged():
    cam = Camera()
    cam.position = np.array([1.0, 2.0, 3.0])
    cam.look_at = np.array([-1.0, -2.0, -3.0])
    initial_look_at = copy(cam.look_at)
    cam.orbit(np.pi / 1.2, np.pi / 3.1)
    assert np.array_equal(cam.look_at, initial_look_at)


def test_orbit_direction_rotated():
    cam = Camera()
    cam.up = np.array([1.0, 1.0, 0.0])
    cam.position = np.array([1.0, 2.0, 3.0])
    cam.look_at = np.array([-3.5, -2.5, -1.5])
    initial_direction = copy(cam.direction)
    cam.orbit(np.pi / 1.2, np.pi / 3.1)
    cos_rotation = np.dot(initial_direction, cam.direction) / (
        np.linalg.norm(initial_direction) * np.linalg.norm(cam.direction)
    )
    assert cos_rotation == approx(np.cos(np.pi / 3.1))


# test position - look_at has unchanged length
def test_orbit_position_look_at_length_unchanged():
    cam = Camera()
    cam.position = np.array([1.0, 2.0, 3.0])
    cam.look_at = np.array([-5.0, -2.5, 1.2])
    initial_length = np.linalg.norm(cam.look_at - cam.position)
    cam.orbit(-np.pi / 1.2, np.pi / 3.1)
    assert np.linalg.norm(cam.look_at - cam.position) == approx(initial_length)


# test rotation axis perpendicular up = angle from up + pi / 2
def test_orbit_up_rotation_axis_angle_90():
    cam = Camera()
    cam.up = np.array([1.0, 1.0, 0.0])
    cam.position = np.array([1.0, 2.0, 3.0])
    cam.look_at = np.array([-3.5, -2.5, -1.5])
    initial_direction = copy(cam.direction)
    initial_perp_up = copy(cam.perpendicular_up)
    # cam.orbit(np.pi / 1.2, np.pi / 3.1)
    cam.orbit(np.pi / 2, np.pi / 3.1)
    rotation_axis = np.cross(cam.direction, initial_direction)
    cos_rotation_axis_angle = np.dot(initial_perp_up, rotation_axis) / (
        np.linalg.norm(initial_perp_up) * np.linalg.norm(rotation_axis)
    )
    assert cos_rotation_axis_angle == approx(np.cos(np.pi / 2 - np.pi / 2))


# test rotation axis perpendicular up = angle from up + pi / 2
def test_orbit_up_rotation_axis_angle():
    cam = Camera()
    cam.up = np.array([1.0, 1.0, 0.0])
    cam.position = np.array([1.0, 2.0, 3.0])
    cam.look_at = np.array([-3.5, -2.5, -1.5])
    initial_direction = copy(cam.direction)
    initial_perp_up = copy(cam.perpendicular_up)
    cam.orbit(np.pi / 1.2, np.pi / 3.1)
    rotation_axis = np.cross(cam.direction, initial_direction)
    print(rotation_axis)
    print(initial_perp_up)
    cos_rotation_axis_angle = np.dot(initial_perp_up, rotation_axis) / (
        np.linalg.norm(initial_perp_up) * np.linalg.norm(rotation_axis)
    )
    assert cos_rotation_axis_angle == approx(np.cos(np.pi / 1.2 - np.pi / 2))


def test_fovx_aspect_ratio_1():
    cam = Camera()
    cam.aspect_ratio = 1.0
    cam.fovy = 37.0
    cam.near = 2.1
    cam.far = 55.3
    assert cam.fovx == cam.fovy


def test_fovx_aspect_ratio_not_1():
    cam = Camera()
    cam.aspect_ratio = 2.3
    cam.fovy = 37.0
    cam.near = 2.1
    cam.far = 55.3
    assert np.tan(np.radians(cam.fovy / 2.0)) * cam.aspect_ratio == approx(
        np.tan(np.radians(cam.fovx / 2.0))
    )


def test_frame_centered():
    cam = Camera()
    cam.points = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    cam.frame(np.array([3.0, 2.0, 1.0]))
    assert np.array_equal(np.array([2.5, 3.5, 4.5]), cam.look_at)


def test_frame_direction_same():
    cam = Camera()
    dir = np.array([3.0, 2.0, 1.0])
    norm_dir = dir / np.linalg.norm(dir)
    cam.points = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    cam.frame(np.array([3.0, 2.0, 1.0]))
    assert np.allclose(norm_dir, cam.direction / np.linalg.norm(cam.direction))


def test_frame_use_cam_direction():
    cam = Camera()
    cam.look_at = np.array([1.0, -2.0, 3.0])
    cam.position = np.array([4.0, 5.0, -6.0])
    init_direction = cam.direction
    cam.points = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    cam.frame()
    assert init_direction / np.linalg.norm(init_direction) == approx(
        cam.direction / np.linalg.norm(cam.direction)
    )


def test_frame_use_cam_up():
    cam = Camera()
    cam.look_at = np.array([1.0, -2.0, 3.0])
    cam.position = np.array([4.0, 5.0, -6.0])
    init_up = cam.up
    cam.points = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    cam.frame(np.array([3.0, 2.0, 1.0]))
    assert init_up / np.linalg.norm(init_up) == approx(cam.up / np.linalg.norm(cam.up))


def test_frame_override_cam_up():
    cam = Camera()
    cam.look_at = np.array([1.0, -2.0, 3.0])
    cam.position = np.array([4.0, 5.0, -6.0])
    init_up = np.array([1.0, 1.0, 1.0])
    cam.points = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    cam.frame(np.array([3.0, 2.0, 1.0]), init_up)
    assert init_up / np.linalg.norm(init_up) == approx(cam.up / np.linalg.norm(cam.up))


def test_frame_points_in_clip_1():
    check_frame_points_in_clip(1.0)


def test_frame_points_in_clip_point_1():
    check_frame_points_in_clip(0.1)


def test_frame_points_in_clip_point_10000():
    check_frame_points_in_clip(10000)


def check_frame_points_in_clip(multiplier):
    __tracebackhide__ = True
    cam = Camera()

    # fmt off
    points = multiplier * np.array(
        [
            [1.0, 2.0, 3.0],
            [4.0, 5.0, 6.0],
            [-3.0, -2.0, 3.5],
            [2.0, -1.0, 4.0],
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.0, 0.0, -1.0],
        ]
    )
    # fmt on
    direction = np.array([3.0, 2.0, 1.0])
    cam.points = points
    cam.frame(direction)
    print(f"fovx: {cam.fovx}; fovy: {cam.fovy}")

    # cam should be pointing along direction
    assert cam.direction / np.linalg.norm(cam.direction) == approx(
        direction / np.linalg.norm(direction),
    )

    # each point should have x, y, z  in [-1, 1]
    for point in points:
        projected_point = cam.projection_matrix.T.dot(
            cam.view_matrix.T.dot(np.append(point, 1.0))
        )
        print("pp:", projected_point[:3] / projected_point[3])
        assert -1.0 <= projected_point[0] / projected_point[3] <= 1.0
        assert -1.0 <= projected_point[1] / projected_point[3] <= 1.0
        assert -1.0 <= projected_point[2] / projected_point[3] <= 1.0


def test_move__forward():
    check_move(1.3)


def check_move(move_by):
    __tracebackhide__ = True
    cam = Camera()
    cam.position = np.array([1.0, 2.0, 3.0])
    # look_at = np.array([-1.0, -4.0, -3.0])
    position_orig = deepcopy(cam.position)
    distance = np.linalg.norm(cam.direction)
    cam.move(move_by)
    assert np.linalg.norm(cam.direction) == approx(distance)
    assert np.linalg.norm(cam.position - position_orig) == approx(abs(move_by))
    assert np.allclose(
        position_orig + cam.direction * move_by / np.linalg.norm(cam.direction),
        cam.position,
    )


def test_move__back():
    check_move(-2.5)


def test_move_up():
    cam = Camera()
    position = np.array([1.0, 2.0, 3.0])
    look_at = np.array([-1.0, -2.0, -5.0])
    cam.position = position
    cam.look_at = look_at
    perp_up = cam.perpendicular_up
    direction = cam.direction
    distance = np.linalg.norm(cam.direction)
    cam.move_up(1.5)
    assert np.linalg.norm(cam.direction) == approx(distance)
    assert np.allclose(cam.direction, direction)
    assert np.allclose(cam.position, position + perp_up * 1.5)
    assert np.allclose(cam.look_at, look_at + perp_up * 1.5)
    assert np.allclose(cam.perpendicular_up, perp_up)


def test_move_right():
    cam = Camera()
    position = np.array([1.0, 2.0, 3.0])
    look_at = np.array([-1.0, -2.0, -5.0])
    cam.position = position
    cam.look_at = look_at
    perp_up = cam.perpendicular_up
    direction = cam.direction
    distance = np.linalg.norm(cam.direction)
    cam.move_right(1.5)
    right = np.cross(cam.direction / np.linalg.norm(cam.direction), cam.up)
    assert np.linalg.norm(cam.direction) == approx(distance)
    assert np.allclose(cam.direction, direction)
    assert np.allclose(cam.position, position + right * 1.5)
    assert np.allclose(cam.look_at, look_at + right * 1.5)
    assert np.allclose(cam.perpendicular_up, perp_up)


def test_move_along():
    cam = Camera()
    position = np.array([1.0, 2.0, 3.0])
    look_at = np.array([-1.0, -2.0, -5.0])
    vector = np.array([-2.0, 3.0, 4.0])
    cam.position = position
    cam.look_at = look_at
    perp_up = cam.perpendicular_up
    cam.move_along(vector)
    assert np.allclose(cam.position, position + vector)
    assert np.allclose(cam.look_at, look_at + vector)
    assert np.allclose(cam.perpendicular_up, perp_up)


def test_move_to_screen():
    cam = Camera()
    position = np.array([1.0, 2.0, 3.0])
    look_at = np.array([-1.0, -2.0, -5.0])
    cam.position = position
    cam.look_at = look_at
    orig_view = cam.view_matrix
    orig_proj = cam.projection_matrix
    perp_up = cam.perpendicular_up
    distance = 1.5
    ndx = 0.6
    ndy = -0.7
    cam.move_to_screen(ndx, ndy, distance)
    displacement = cam.position - position
    assert np.linalg.norm(displacement) == approx(distance)
    assert np.allclose(cam.direction, look_at - position)
    assert np.allclose(cam.perpendicular_up, perp_up)
    # TODO: check that the new position transformed with the original
    # view and projection are at ndx, ndy
    position_screen_coords = orig_proj.T.dot(
        orig_view.T.dot(np.append(cam.position, 1.0))
    )
    assert position_screen_coords[0] / position_screen_coords[3] == approx(ndx)
    assert position_screen_coords[1] / position_screen_coords[3] == approx(ndy)
