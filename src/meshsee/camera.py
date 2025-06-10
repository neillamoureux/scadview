import numpy as np
from numpy.typing import NDArray
from pyrr import matrix33, matrix44

from meshsee.observable import Observable
from meshsee.shader_program import ShaderVar


def intersection(
    range1: tuple[float, float] | None, range2: tuple[float, float] | None
) -> tuple[float, float] | None:
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
        self.points = np.array(
            [
                [1.0, 1.0, 1.0],
            ],
            dtype="f4",
        )
        self.up = self.Z_DIR
        self.fovy = self.FOVY_INIT
        self._aspect_ratio = 1.0
        self.near = self.NEAR_INIT
        self.far = self.FAR_INIT
        self.on_program_value_change = Observable()

    @property
    def direction(self) -> NDArray[np.float32]:
        return self.look_at - self.position

    @property
    def aspect_ratio(self):
        return self._aspect_ratio

    @aspect_ratio.setter
    def aspect_ratio(self, value: float):
        self._aspect_ratio = value
        self.update_matrices()

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
        self.on_program_value_change.notify(ShaderVar.VIEW_MATRIX, vm)
        return vm

    @property
    def projection_matrix(self) -> NDArray[np.float32]: ...

    @property
    def points(self) -> NDArray[np.float32]:
        return self._points

    @points.setter
    def points(self, value: NDArray[np.float32]):
        self._points = value

    def update_matrices(self):
        self._update_far_near()
        self.view_matrix
        self.projection_matrix

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
        self.update_matrices()

    @property
    def fovx(self):
        return np.rad2deg(
            2 * np.arctan(np.tan(np.radians(self.fovy) / 2) * self.aspect_ratio)
        )

    def frame(
        self,
        direction: NDArray[np.float32] | None = None,
        up: NDArray[np.float32] | None = None,
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
        center = np.mean(self.points, axis=0)
        self.look_at = center
        self.position = center - direction
        norm_direction = direction / np.linalg.norm(direction)
        bb = self._bounding_box_in_cam_space()
        abs_x_max = np.max(np.abs(bb[:, 0]))
        abs_y_max = np.max(np.abs(bb[:, 1]))
        max_z = np.max(
            bb[:, 2]
        )  # distance to closest plane( +z closer to camera); if positive, plane is behind camera
        x_dist = abs_x_max / np.tan(np.radians(self.fovx) / 2)
        y_dist = abs_y_max / np.tan(np.radians(self.fovy) / 2)
        dist = max(x_dist, y_dist)
        self.position = center - direction - norm_direction * (max_z + dist)
        self._update_far_near()
        self.update_matrices()

    def _update_far_near(self):
        bb = self._bounding_box_in_cam_space()
        self.far = -np.min(bb[:, 2]) * self.FAR_MULTIPLIER
        self.far = max(1.0, self.far)
        self.near = self.far / self.FAR_NEAR_RATIO

    def _bounding_box_in_cam_space(self) -> NDArray[np.float32]:
        """
        Find the bounding box of the points.
        """
        points_4d = np.append(self.points, np.ones((self.points.shape[0], 1)), axis=1)
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
        # frustum_matrix = projection_matrix @ view_matrix

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
            if plane[axis] == 0.0:
                continue
            else:
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
        self.update_matrices()

    # move the camera along the up vector
    def move_up(self, distance):
        displacement = self.perpendicular_up * distance
        self.position = self.position + displacement
        self.look_at = self.look_at + displacement
        self.update_matrices()

    # move the camera along the right vector
    def move_right(self, distance):
        right = np.cross(self.direction / np.linalg.norm(self.direction), self.up)
        self.position = self.position + right * distance
        self.look_at = self.look_at + right * distance
        self.update_matrices()

    def move_along(self, vector):
        self.position = self.position + vector
        self.look_at = self.look_at + vector
        self.update_matrices()

    def move_to_screen(self, ndx: float, ndy: float, distance: float):
        """
        Move the camera to the normalized screen coordinates ndx, ndy
        """
        ...


class CameraPerspective(Camera):
    def __init__(self):
        super().__init__()

    @property
    def projection_matrix(self) -> NDArray[np.float32]:
        pm = matrix44.create_perspective_projection(
            self.fovy, self.aspect_ratio, self.near, self.far, dtype="f4"
        )
        self.on_program_value_change.notify(ShaderVar.PROJECTION_MATRIX, pm)
        return pm

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


class CameraOrthogonal(Camera):
    # Treat as the perspective cam,
    # that has been moved to infinity and zoomed in
    # preserving the width of the view at origin.
    #
    # So top = norm(position) * tan(fovy / 2)
    #
    def __init__(self):
        super().__init__()

    @property
    def top(self):
        return np.tan(np.radians(self.fovy / 2)) * self._distance_to_focal_plane()

    def _distance_to_focal_plane(self):
        # We want distance from position to plane perp to direction and through origin
        # So x where (position + x (direction) / norm(direction)) . distance  = 0
        # -> x = - position . direction / norm(direction)
        return -np.dot(self.position, self.direction) / np.linalg.norm(self.direction)

    @property
    def right(self):
        return self.top * self.aspect_ratio

    @property
    def projection_matrix(self) -> NDArray[np.float32]:
        pm = matrix44.create_orthogonal_projection(
            -self.right,
            self.right,
            -self.top,
            self.top,
            self.near,
            self.far,
            dtype="f4",
        )
        self.on_program_value_change.notify(ShaderVar.PROJECTION_MATRIX, pm)
        return pm

    def move_to_screen(self, ndx: float, ndy: float, distance: float):
        """
        Move the camera to the normalized screen coordinates ndx, ndy
        """
        position_clip_coords = (
            self.projection_matrix.T
            @ self.view_matrix.T
            @ np.append(self.position, 1.0)
        )
        position_clip_coords = position_clip_coords[:3] / position_clip_coords[3]

        # Get the pointer view coords on the plane through position (perp to direction)
        # Since the projection maps perp to direction, we can use the inverse of the projection matrix
        pointer_view_coords = np.linalg.inv(self.projection_matrix.T).dot(
            np.array([ndx, ndy, position_clip_coords[2], 1.0])
        )

        # Get the world coords of the pointer on the plane (perp to direction ) through position.
        # Note that position - pointer_world_coords should be perpendicular to direction
        pointer_world_coords = np.linalg.inv(self.view_matrix.T).dot(
            pointer_view_coords
        )
        pointer_world_coords = pointer_world_coords[:3] / pointer_world_coords[3]
        perp_direction = pointer_world_coords - self.position

        # Get the scaling factor
        old_fp_distance = self._distance_to_focal_plane()
        self.move_along(self.direction / np.linalg.norm(self.direction) * distance)
        new_fp_distance = self._distance_to_focal_plane()
        s = old_fp_distance / new_fp_distance

        # s is the scaling amount, which moves the ndc of the points "underneath" the normalized ddvice coords (ndx, ndy)
        # to (s * ndx, s * ndy).  We want to shift the center so that (s * ndx, s * ndy) is back moved
        # back to (ndx, ndy) - that it, move the center to ((s - 1) * ndx, (s - 1) * ndy).
        # In world coordinates, this means moving in a direction perependicular to the direction
        # We calculated this perp direction before scaling, so we need to divide by s to get the
        # correct distance after scaling.

        self.move_along(perp_direction * (s - 1.0) / s)


def copy_camera_state(from_camera: Camera, to_camera: Camera):
    to_camera.points = from_camera.points
    to_camera.look_at = from_camera.look_at
    to_camera.position = from_camera.position
    to_camera.up = from_camera.up
    to_camera.aspect_ratio = from_camera.aspect_ratio
