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
    cam = Camera()
    cam.aspect_ratio = 2.0
    cam.fovy = 90.0
    cam.near = 1.0
    cam.far = 100.0
    projection_matrix = cam.projection_matrix
    assert projection_matrix.shape == (4, 4)
    # near should map to [0, 0, 1] in clip space, or in 4 dim [0, 0, z, z], z arbitrary
    near_product = projection_matrix.dot(np.array([0.0, 0.0, -cam.near, 1.0]))
    # assert near_product == approx(np.array([0.0, 0.0, 1.0, -1.0])) # just to see the values
    assert near_product[0:2] == approx(np.array([0.0, 0.0]))
    assert near_product[2] == approx(-near_product[3])
    # far should map to [0, 0, -1] in clip space, or in 4 dim [0, 0, z, -z], z arbitrary
    far_product = projection_matrix.dot(np.array([0.0, 0.0, -cam.far, 1.0]))
    # assert far_product == approx(np.array([0.0, 0.0, 1.0, -1.0])) # just to see the values
    assert far_product[0:2] == approx(np.array([0.0, 0.0]))
    assert far_product[2] == approx(far_product[3])


def test_approx():
    assert np.array([1.0, 2.0]) == approx(np.array([1.0, 2.0]))
