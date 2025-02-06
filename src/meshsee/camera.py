import numpy as np
from pyrr import matrix33, matrix44


class Camera:
    POSITION_INIT = np.array([2.0, 2.0, 2.0], dtype="f4")
    LOOK_AT_INIT = np.array([0.0, 0.0, 0.0], dtype="f4")
    Z_DIR = np.array([0.0, 0.0, 1.0], dtype="f4")
    FOVY_INIT = 22.5
    NEAR_INIT = 0.1
    FAR_INIT = 1000.0

    def __init__(self):
        self.position = self.POSITION_INIT
        self.look_at = np.array([0.0, 0.0, 0.0], dtype="f4")
        self.up = self.Z_DIR
        self.fovy = self.FOVY_INIT
        self.aspect_ratio = 1.0
        self.near = self.NEAR_INIT
        self.far = self.FAR_INIT

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
        return matrix44.create_look_at(self.position, self.look_at, self.up, dtype="f4")

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
