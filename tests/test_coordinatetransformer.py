import env
import pytest
import numpy as np
from coordinatetransformer import CoordinateTransformer


def test_angles_already_in_degrees_are_unchanged():
    angle = 4.2
    transformer = CoordinateTransformer(angles_in_degrees=True)
    assert angle == transformer.get_angle_in_degrees(angle)


def test_angles_in_radians_are_converted():
    angle_in_rad = np.pi
    angle_in_deg = 180.0
    transformer = CoordinateTransformer(angles_in_degrees=False)
    assert abs(transformer.get_angle_in_degrees(angle_in_rad) - angle_in_deg) < 0.0001


def test_convert_spherical_to_cartesian():
    transformer = CoordinateTransformer()
    np.testing.assert_allclose(transformer.spherical_to_cartesian([1.0, 0.0, 0.0]), [0.0, 0.0, 1.0], atol=1e-7)
    np.testing.assert_allclose(transformer.spherical_to_cartesian([1.0, 90.0, 0.0]), [1.0, 0.0, 0.0], atol=1e-7)
    np.testing.assert_allclose(transformer.spherical_to_cartesian([1.0, 90.0, 90.0]), [0.0, 1.0, 0.0], atol=1e-7)


def test_convert_cartesian_to_spherical():
    transformer = CoordinateTransformer()
    np.testing.assert_allclose(transformer.cartesian_to_spherical([0.0, 0.0, 1.0]), [1.0, 0.0, 0.0], atol=1e-7)
    np.testing.assert_allclose(transformer.cartesian_to_spherical([1.0, 0.0, 0.0]), [1.0, 90.0, 0.0], atol=1e-7)
    np.testing.assert_allclose(transformer.cartesian_to_spherical([0.0, 1.0, 0.0]), [1.0, 90.0, 90.0], atol=1e-7)
