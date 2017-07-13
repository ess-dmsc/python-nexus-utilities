import env
import pytest
import numpy as np
from nexusutils import *


def test_is_scalar_true():
    assert is_scalar(1)


def test_is_scalar_true_list():
    assert is_scalar([1])


def test_is_scalar_true_array():
    assert is_scalar(np.array([1]))


def test_is_scalar_false_list():
    assert not is_scalar([1, 2])


def test_is_scalar_false_array():
    assert not is_scalar(np.array([1, 2]))


def test_normalise_zeros_magnitude():
    result_vector, result_mag = normalise(np.array([0.0, 0.0, 0.0]))
    assert np.isclose(np.array([result_mag]), np.array([0.0]))


def test_normalise_zeros_vector():
    result_vector, result_mag = normalise(np.array([0.0, 0.0, 0.0]))
    assert np.allclose(result_vector, np.array([0.0, 0.0, 0.0]))


def test_normalise_vector_magnitude():
    result_vector, result_mag = normalise(np.array([1.0, 1.0, 2.0]))
    assert np.isclose(np.array([result_mag]), np.array([np.sqrt(6.0)]))


def test_normalise_vector_multiple_components():
    result_vector, result_mag = normalise(np.array([1.0, 1.0, 1.0]))
    assert np.allclose(result_vector, np.array([np.sqrt(3.0) / 3., np.sqrt(3.0) / 3., np.sqrt(3.0) / 3.]))


def test_normalise_vector():
    result_vector, result_mag = normalise(np.array([0.0, 3.7, 0.0]))
    assert np.allclose(result_vector, np.array([0.0, 1.0, 0.0]))


def test_find_rotation_matrix_between_vectors_coincide():
    vector_a = np.array([1.0, 0.0, 0.5])
    vector_b = np.array([1.0, 0.0, 0.5])
    rotation_matrix = find_rotation_matrix_between_vectors(vector_a, vector_b)
    # The vectors coincide so the rotation matrix should do nothing when multipled to a vector
    # (should be the identity matrix)
    assert np.allclose(rotation_matrix, np.identity(3, float))


def test_find_rotation_matrix_between_vectors():
    vector_a = np.array([1.0, 0.0, 0.0])
    vector_b = np.array([0.0, 1.0, 0.0])
    rotation_matrix = find_rotation_matrix_between_vectors(vector_a, vector_b)
    # The vectors coincide so the rotation matrix should do nothing when multipled to a vector
    # (should be the identity matrix)
    assert np.allclose(rotation_matrix, np.array([[1., 2., 0.], [0., 1., 0.], [0., 0., 1.]]))


def test_get_an_orthogonal_unit_vector_is_orthogonal():
    input = np.array([0.5, 0.7, 0.1])
    result = get_an_orthogonal_unit_vector(input)
    dot_product = np.dot(input, result)
    assert np.isclose(np.array([dot_product]), np.array([0.0]))


def test_get_an_orthogonal_unit_vector_is_unit():
    input = np.array([0.1, 0.7, 0.5])
    result = get_an_orthogonal_unit_vector(input)
    result_unit, result_mag = normalise(result)
    assert np.isclose(np.array([result_mag]), np.array([1.0]))
