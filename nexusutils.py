import numpy as np
import logging

"""
Free-function utilities for use by the NexusBuilder
"""

logger = logging.getLogger('NeXus_Builder')


def isclose(a, b, rel_tol=1e-09, abs_tol=0.0):
    return abs(a-b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)


def is_scalar(object_to_check):
    if hasattr(object_to_check, '__len__'):
        return len(object_to_check) == 1
    return True


def normalise(input_vector):
    """
    Normalise to unit vector

    :param input_vector: Input vector (numpy array)
    :return: Unit vector, magnitude
    """
    magnitude = np.sqrt(np.sum(np.square(input_vector.astype(float))))
    if magnitude == 0:
        return np.array([0.0, 0.0, 0.0]), 0.0
    unit_vector = input_vector.astype(float) / magnitude
    return unit_vector, magnitude


def find_rotation_matrix_between_vectors(vector_a, vector_b):
    """
    Find the 3D rotation matrix to rotate vector_a onto vector_b

    :param vector_a: 3D vector
    :param vector_b: 3D vector
    :return: 3D rotation matrix
    """
    unit_a, mag_a = normalise(vector_a)
    unit_b, mag_b = normalise(vector_b)
    identity_matrix = np.identity(3)

    if np.allclose(unit_a, unit_b):
        return identity_matrix

    axis, angle = find_rotation_axis_and_angle_between_vectors(vector_a, vector_b)

    skew_symmetric = np.array([np.array([0.0, -axis[2], axis[1]]),
                               np.array([axis[2], 0.0, -axis[0]]),
                               np.array([-axis[1], axis[0], 0.0])])

    rotation_matrix = identity_matrix + np.sin(angle) * skew_symmetric + \
                      ((1.0 - np.cos(angle)) * (skew_symmetric ** 2.0))
    return rotation_matrix


def find_rotation_axis_and_angle_between_vectors(vector_a, vector_b):
    """
    Find the axis and angle of rotation to rotate vector_a onto vector_b

    :param vector_a: 3D vector
    :param vector_b: 3D vector
    :return: axis, angle
    """
    unit_a, mag_a = normalise(vector_a)
    unit_b, mag_b = normalise(vector_b)

    if np.allclose(unit_a, unit_b):
        logger.debug(
            'Vectors coincide; no rotation required in nexusutils.find_rotation_axis_and_angle_between_vectors')
        return None, None

    cross_prod = np.cross(vector_a, vector_b)
    unit_cross, mag_cross = normalise(cross_prod)

    if isclose(mag_cross, 0.0):
        raise NotImplementedError('No unique solution for rotation axis in '
                                  'nexusutils.find_rotation_axis_and_angle_between_vectors')

    axis = cross_prod / mag_cross
    angle = -1.0 * np.arccos(np.dot(vector_a, vector_b) / (mag_a * mag_b))

    return axis, angle


def rotation_matrix_from_axis_and_angle(axis, theta):
    """
    Calculate the rotation matrix for rotating angle theta about axis

    :param axis: 3D unit vector axis
    :param theta: Angle to rotate about axis in radians
    :return: 3x3 rotation matrix
    """
    axis_x = axis[0]
    axis_y = axis[1]
    axis_z = axis[2]
    cos_t = np.cos(theta)
    sin_t = np.sin(theta)
    rotation_matrix_row_1 = np.array([cos_t + axis_x ** 2.0 * (1 - cos_t),
                                      axis_x * axis_y * (1 - cos_t) - axis_z * sin_t,
                                      axis_x * axis_z * (1 - cos_t) + axis_y * sin_t])
    rotation_matrix_row_2 = np.array([axis_y * axis_x * (1 - cos_t) + axis_z * sin_t,
                                      cos_t + axis_y ** 2.0 * (1 - cos_t),
                                      axis_y * axis_z * (1 - cos_t) - axis_x * sin_t])
    rotation_matrix_row_3 = np.array([axis_z * axis_x * (1 - cos_t) - axis_y * sin_t,
                                      axis_z * axis_y * (1 - cos_t) + axis_x * sin_t,
                                      cos_t + axis_z ** 2.0 * (1 - cos_t)])
    rotation_matrix = np.array([rotation_matrix_row_1, rotation_matrix_row_2, rotation_matrix_row_3])
    return rotation_matrix


def get_an_orthogonal_unit_vector(input_vector):
    """
    Return a unit vector which is orthogonal to the input vector
    There are infinite valid solutions, just one is returned

    :param input_vector: 3D vector as a numpy array
    :return: 3D vector as a numpy array, orthogonal to input_vector
    """
    if np.abs(input_vector[2]) < np.abs(input_vector[0]):
        vector = np.array([input_vector[1], -input_vector[0], 0.])
        unit_vector, mag = normalise(vector)
        return unit_vector
    vector = np.array([0., -input_vector[2], input_vector[1]])
    unit_vector, mag = normalise(vector)
    return unit_vector
