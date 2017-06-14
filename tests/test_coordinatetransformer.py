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
