from copy import copy
from math import acos, cos

from pytest import approx, mark
import numpy as np

from meshsee.camera import Camera


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
    approx(view_matrix * np.append(cam.look_at, 1.0), np.array([0.0, 0.0, 0.0, 1.0]))
    approx(view_matrix * np.append(cam.up, 1.0), np.array([0.0, 1.0, 0.0, 1.0]))


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


@mark.skip(reason="Not sure how to test")
def test_projection_matrix2():
    # Note: OpenGL is right-handed, so the z-axis is pointing out of the screen back to the viewer
    cam = Camera()
    cam.aspect_ratio = 2.0
    cam.fovy = 45.0
    cam.near = 1.0
    cam.far = 100.0
    projection_matrix = cam.projection_matrix
    assert projection_matrix.shape == (4, 4)
    # near should map to [0, 0, 1] in clip space, or in 4 dim [0, 0, z, z], z arbitrary
    near_product = projection_matrix.dot(np.array([0.0, 0.0, -cam.near, 1.0]))
    assert near_product[0:2] == approx(np.array([0.0, 0.0]))
    assert near_product[2] == approx(near_product[3])
    # far should map to [0, 0, -1] in clip space, or in 4 dim [0, 0, z, -z], z arbitrary
    far_product = projection_matrix.dot(np.array([0.0, 0.0, -cam.far, 1.0]))
    assert far_product[0:2] == approx(np.array([0.0, 0.0]))
    # assert far_product[2] / far_product[3] == approx(-1.0)
    assert far_product[2] == approx(-far_product[3])


# test fovy
@mark.skip(reason="Not sure how to test")
def test_projection_matrix3():
    # Note: OpenGL is right-handed, so the z-axis is pointing out of the screen back to the viewer
    cam = Camera()
    cam.aspect_ratio = 2.0
    cam.fovy = 45.0
    cam.near = 1.0
    cam.far = 100.0
    projection_matrix = cam.projection_matrix
    assert projection_matrix.shape == (4, 4)
    #  aspect_ratio * tan(fovy/2),tan(fov/2), near should map to [1.0, 1.0, 1] in clip space, or in 4 dim [1, z, z, z], z arbitrary
    y = cam.near * np.tan(np.radians(cam.fovy) / 2)
    x = y * cam.aspect_ratio
    near_product = projection_matrix.dot(np.array([x, y, -cam.near, 1.0]))
    assert near_product / near_product[3] == approx(np.array([1.0, 1.0, 1.0, 1.0]))


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
