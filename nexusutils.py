import numpy as np

"""
Free-function utilities for use by the NexusBuilder
"""


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


def find_rotation_between_vectors(vector_a, vector_b):
    """
    Find the 3D rotation matrix to rotate vector_a onto vector_b

    :param vector_a: 3D unit vector
    :param vector_b: 3D unit vector
    :return: 3D rotation matrix
    """
    identity_matrix = np.identity(3)
    cross_product = np.cross(vector_a, vector_b)
    cosine_of_angle = np.dot(vector_a, vector_b)
    if cosine_of_angle == -1.0:
        raise NotImplementedError('Need to implement calculation of rotation '
                                  'matrix when vectors point in opposite directions')
    elif np.array_equal(vector_a, vector_b):
        rotation_matrix = identity_matrix
    else:
        rotation_matrix = identity_matrix + cross_product + (cross_product ** 2.0) * (1.0 / (1 + cosine_of_angle))
    return rotation_matrix


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
