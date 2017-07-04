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
    unit_vector = input_vector.astype(float)/magnitude
    return unit_vector, magnitude


def find_rotation(vector_a, vector_b):
    """
    Find the 3D rotation matrix to rotate vector_a onto vector_b

    :param vector_a: 3D vector
    :param vector_b: 3D vector
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
        rotation_matrix = identity_matrix + cross_product + (cross_product**2.0)*(1.0/(1 + cosine_of_angle))
    return rotation_matrix
