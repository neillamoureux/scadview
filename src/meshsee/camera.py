import numpy as np
from pyrr import matrix33, matrix44

from meshsee.observable import Observable
from meshsee.program_updater import ProgramValues


def point_center(points: np.ndarray) -> np.ndarray:
    return np.mean(points, axis=0)


def intersection(range1: tuple[float], range2: tuple[float]) -> tuple[float] | None:
    """
    Compute the intersection of two ranges.
    The result is a tuple (min, max) where min and max are the
    minimum and maximum coordinates of the intersection.
    Returns None if no intersection exists.
    """
    if range1 is None or range2 is None:
        return None
    result = (max(range1[0], range2[0]), min(range1[1], range2[1]))
    if result[0] > result[1]:
        return None
    return result


class Camera:
    POSITION_INIT = np.array([2.0, 2.0, 2.0], dtype="f4")
    LOOK_AT_INIT = np.array([0.0, 0.0, 0.0], dtype="f4")
    Z_DIR = np.array([0.0, 0.0, 1.0], dtype="f4")
    FOVY_INIT = 22.5
    FAR_NEAR_RATIO = 2000.0
    FAR_MULTIPLIER = 2.0
    NEAR_INIT = 1.0
    FAR_INIT = NEAR_INIT * FAR_NEAR_RATIO

    def __init__(self):
        self.position = self.POSITION_INIT
        self.look_at = np.array([0.0, 0.0, 0.0], dtype="f4")
        self.up = self.Z_DIR
        self.fovy = self.FOVY_INIT
        self.aspect_ratio = 1.0
        self.near = self.NEAR_INIT
        self.far = self.FAR_INIT
        self.on_program_value_change = Observable()

    @property
    def direction(self):
        return self.look_at - self.position

    @property
    def perpendicular_up(self):
        """
        The up vector is not necessarily orthogonal to the direction vector.
        So we need to compute a vector that is orthogonal to the direction vector
        and is in the same plane as the up and direction vectors.
        That is, project the up vector onto the plane orthogonal to the direction vector
        and normalize the result.
        """
        normalized_direction = self.direction / np.linalg.norm(self.direction)
        up_along_direction = (
            np.dot(self.up, normalized_direction) * normalized_direction
        )
        up_projection = self.up - up_along_direction
        perp_up = up_projection / np.linalg.norm(up_projection)
        return perp_up

    @property
    def view_matrix(self):
        vm = matrix44.create_look_at(self.position, self.look_at, self.up, dtype="f4")
        self.on_program_value_change.notify(ProgramValues.CAMERA_MATRIX, vm)
        return vm

    @property
    def projection_matrix(self) -> np.ndarray:
        return matrix44.create_perspective_projection(
            self.fovy, self.aspect_ratio, self.near, self.far, dtype="f4"
        )

    def orbit(self, angle_from_up, rotation_angle):
        """
        Rotate the camera around the look_at point.
        Angles are in radians.
        """
        # perp_up = self.up
        perp_up = self.perpendicular_up
        rotated_up_mat = matrix33.create_from_axis_rotation(
            self.direction, angle_from_up, dtype="f4"
        )
        rotated_up = matrix33.apply_to_vector(rotated_up_mat, self.up)
        rotation_axis = np.cross(self.direction, rotated_up)
        rotation = matrix33.create_from_axis_rotation(
            rotation_axis, rotation_angle, dtype="f4"
        )
        new_direction = matrix33.apply_to_vector(rotation, self.direction)
        new_up = matrix33.apply_to_vector(rotation, perp_up)
        self.position = self.look_at - new_direction
        self.up = new_up

    @property
    def fovx(self):
        return np.rad2deg(
            2 * np.arctan(np.tan(np.radians(self.fovy) / 2) * self.aspect_ratio)
        )

    def frame(
        self,
        points: np.ndarray,
        direction: np.ndarray | None = None,
        up: np.ndarray | None = None,
    ):
        """
        Frame the points with the camera.
        """
        if direction is None:
            direction = self.direction
        if up is None:
            up = self.up
        else:
            self.up = up
        center = np.mean(points, axis=0)
        self.look_at = center
        self.position = center - direction
        norm_direction = direction / np.linalg.norm(direction)
        bb = self._bounding_box_in_cam_space(points)
        abs_x_max = np.max(np.abs(bb[:, 0]))
        abs_y_max = np.max(np.abs(bb[:, 1]))
        max_z = np.max(
            bb[:, 2]
        )  # distance to closest plane( +z closer to camera); if positive, plane is behind camera
        x_dist = abs_x_max / np.tan(np.radians(self.fovx) / 2)
        y_dist = abs_y_max / np.tan(np.radians(self.fovy) / 2)
        dist = max(x_dist, y_dist)
        self.position = center - direction - norm_direction * (max_z + dist)
        new_bb = self._bounding_box_in_cam_space(points)
        self.far = -np.min(new_bb[:, 2]) * self.FAR_MULTIPLIER
        self.near = self.far / self.FAR_NEAR_RATIO

    def _bounding_box_in_cam_space(self, points: np.ndarray) -> np.ndarray:
        """
        Find the bounding box of the points.
        """
        points_4d = np.append(points, np.ones((points.shape[0], 1)), axis=1)
        view_points = points_4d.dot(self.view_matrix)
        view_points = view_points / view_points[:, 3][:, np.newaxis]
        return np.array([np.min(view_points, axis=0), np.max(view_points, axis=0)])

    def _frustum_planes(self):
        """
        Compute the frustum planes as a shape (6,4) matrix
        Each row (a, b, c, d) where (a, b, c) is the normal vector of the plane
        pointing into the frustum.
        and d is such that (a, b, c) dot (x, y, z) + d = 0
        """
        view_matrix = self.view_matrix
        projection_matrix = self.projection_matrix
        frustum_matrix = projection_matrix.T @ view_matrix.T

        planes = np.zeros((6, 4), dtype="f4")
        # Left
        planes[0] = frustum_matrix[3] + frustum_matrix[0]
        # Right
        planes[1] = frustum_matrix[3] - frustum_matrix[0]
        # Bottom
        planes[2] = frustum_matrix[3] + frustum_matrix[1]
        # Top
        planes[3] = frustum_matrix[3] - frustum_matrix[1]
        # Near
        planes[4] = frustum_matrix[3] + frustum_matrix[2]
        # Far
        planes[5] = frustum_matrix[3] - frustum_matrix[2]

        # Normalize the normal vector and adjust d
        for i in range(6):
            planes[i] = planes[i] / np.linalg.norm(planes[i][:3])

        return planes

    def axis_visible_range(self, axis: int):
        """
        Compute the visible range of the axis in world space.
        The result is a tuple (min, max) where min and max are the
        minimum and maximum coordinates of the axis that are visible in the frustum.
        """
        planes = self._frustum_planes()
        range = (-np.inf, np.inf)
        # planes are in the form (a, b, c, d) where (a, b, c) is the normal vector
        # of the plane and d is such that (a, b, c) dot (x, y, z) + d = 0
        # For the x axis, (a, b, c) dot (x, 0, 0 ) = -d
        # ax = -d
        # x = -d / a
        # The normals point inward, so (a, b, c) dot (x, y, z) + d > 0 means the point is
        # on the visible side of the plane
        # so if x = inf, a * inf + d > 0 if a > 0, otherwise < 0

        for plane in planes:
            intersects_at = -plane[3] / plane[axis]
            if plane[axis] > 0:
                plane_range = (intersects_at, np.inf)
            else:
                plane_range = (-np.inf, intersects_at)
            range = intersection(range, plane_range)
        return range

    # move the camera along the direction vector
    # without changing the look_at point
    def move(self, distance):
        vector = self.direction * distance / np.linalg.norm(self.direction)
        self.position = self.position + vector
        self.look_at = self.look_at + vector

    # move the camera along the up vector
    def move_up(self, distance):
        displacement = self.perpendicular_up * distance
        self.position = self.position + displacement
        self.look_at = self.look_at + displacement

    # move the camera along the right vector
    def move_right(self, distance):
        right = np.cross(self.direction / np.linalg.norm(self.direction), self.up)
        self.position = self.position + right * distance
        self.look_at = self.look_at + right * distance

    def move_along(self, vector):
        self.position = self.position + vector
        self.look_at = self.look_at + vector

    def move_to_screen(self, ndx: float, ndy: float, distance: float):
        """
        Move the camera to the normalized screen coordinates ndx, ndy
        """
        eye_pos_on_far = np.linalg.inv(self.projection_matrix.T).dot(
            np.array([ndx, ndy, 1.0, 1.0])
        )
        pos_on_far = np.linalg.inv(self.view_matrix.T).dot(eye_pos_on_far)
        ray_vector = pos_on_far[:3] / pos_on_far[3] - self.position
        ray_vector = ray_vector / np.linalg.norm(ray_vector) * distance
        self.move_along(ray_vector)
