import pytest
import numpy as np
from nexusutils.utils import *


def test_is_scalar_returns_true_for_single_value():
    assert is_scalar(1)


def test_is_scalar_returns_true_for_single_value_in_a_list():
    assert is_scalar([1])


def test_is_scalar_returns_true_for_single_value_in_an_array():
    assert is_scalar(np.array([1]))


def test_is_scalar_returns_false_for_more_than_one_value_in_a_list():
    assert not is_scalar([1, 2])


def test_is_scalar_returns_false_for_more_than_one_value_in_an_array():
    assert not is_scalar(np.array([1, 2]))


def test_normalise_returns_zero_magnitude_for_vector_of_zeros():
    result_vector, result_mag = normalise(np.array([0.0, 0.0, 0.0]))
    assert np.isclose(np.array([result_mag]), np.array([0.0]))


def test_normalise_returns_vector_of_zeros_for_vector_of_zeros():
    result_vector, result_mag = normalise(np.array([0.0, 0.0, 0.0]))
    assert np.allclose(result_vector, np.array([0.0, 0.0, 0.0]))


def test_normalise_returns_magnitude_for_non_zero_vector():
    result_vector, result_mag = normalise(np.array([1.0, 1.0, 2.0]))
    assert np.isclose(np.array([result_mag]), np.array([np.sqrt(6.0)]))


input_vectors = [
    np.array([0.0, 3.7, 0.0]),
    np.array([1.3, 2.4, 0.0]),
    np.array([1.2, 5.1, 0.6]),
]


@pytest.mark.parametrize("input_vector", input_vectors)
def test_normalise_returns_a_unit_vector_for_non_unit_input_vectors(input_vector):
    result_vector, result_mag = normalise(input_vector)
    assert is_close(1.0, np.linalg.norm(result_vector))


def test_rotation_matrix_for_coinciding_input_vectors_is_identity_matrix():
    vector_a = np.array([1.0, 0.0, 0.5])
    vector_b = np.array([1.0, 0.0, 0.5])
    rotation_matrix = find_rotation_matrix_between_vectors(vector_a, vector_b)
    assert np.allclose(rotation_matrix, np.identity(3, float))


def test_find_rotation_matrix_between_vectors():
    vector_a = np.array([1.0, 0.0, 0.0])
    vector_b = np.array([0.0, 1.0, 0.0])
    rotation_matrix = find_rotation_matrix_between_vectors(vector_a, vector_b)
    assert np.allclose(
        rotation_matrix, np.array([[1.0, 2.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    )


def test_get_an_orthogonal_unit_vector_returns_an_orthogonal_vector():
    input = np.array([0.5, 0.7, 0.1])
    result = get_an_orthogonal_unit_vector(input)
    dot_product = np.dot(input, result)
    assert is_close(0.0, dot_product, abs_tol=1e-10)


def test_get_an_orthogonal_unit_vector_returns_a_unit_vector():
    input = np.array([0.1, 0.7, 0.5])
    result = get_an_orthogonal_unit_vector(input)
    result_unit, result_mag = normalise(result)
    assert is_close(result_mag, 1.0)


def test_find_rotation_axis_and_angle_between_orthogonal_vectors_gives_90_degree_angle():
    vector_a = np.array([1.0, 0.0, 0.0])
    vector_b = np.array([0.0, 1.0, 0.0])
    axis, angle = find_rotation_axis_and_angle_between_vectors(vector_a, vector_b)
    assert is_close(angle, np.deg2rad(-90.0))


def test_find_rotation_axis_and_angle_between_orthogonal_vectors_gives_mutually_orthogonal_axis():
    vector_a = np.array([1.0, 0.0, 0.0])
    vector_b = np.array([0.0, 1.0, 0.0])
    axis, angle = find_rotation_axis_and_angle_between_vectors(vector_a, vector_b)
    assert np.allclose(axis, np.array([0.0, 0.0, 1.0]))


def test_find_rotation_axis_and_angle_between_coinciding_vectors_returns_None():
    vector_a = np.array([1.0, 0.0, 0.0])
    vector_b = np.array([1.0, 0.0, 0.0])
    axis, angle = find_rotation_axis_and_angle_between_vectors(vector_a, vector_b)
    assert axis is None
    assert angle is None


def test_find_rotation_axis_and_angle_between_opposing_vectors_throws():
    vector_a = np.array([1.0, 0.0, 0.0])
    vector_b = np.array([-1.0, 0.0, 0.0])
    with pytest.raises(NotImplementedError):
        axis, angle = find_rotation_axis_and_angle_between_vectors(vector_a, vector_b)


def test_rotation_matrix_from_axis_and_angle():
    axis = np.array([0.0, 0.0, 1.0])
    angle = np.deg2rad(-90.0)
    rotation_matrix = rotation_matrix_from_axis_and_angle(axis, angle)
    assert np.allclose(
        rotation_matrix, np.array([[0.0, 1.0, 0.0], [-1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    )
