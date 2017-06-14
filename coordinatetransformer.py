import numpy as np
import math3d as m3d


class CoordinateTransformer:
    def __init__(self, angles_in_degrees=True, nexus_coords=None):
        if nexus_coords is None:
            nexus_coords = ['x', 'y', 'z']

    @staticmethod
    def math3d_example():
        # A rotation of 1 radian around the axis (1,2,3)
        r = m3d.Orientation.new_axis_angle([1, 2, 3], 1)
        # v = m3d.Vector(4, 5, 6) or as a numpy array like this:
        v = m3d.Vector(np.array([4, 5, 6]))
        # Apply rotation to vector v
        result = r * v
        # Convert result to a numpy array
        print(result.get_array())

    @staticmethod
    def spherical_to_cartesian(rthetaphi):
        # takes list rthetaphi (single coordinate)
        r = rthetaphi[0]
        theta = rthetaphi[1] * np.pi / 180  # to radian
        phi = rthetaphi[2] * np.pi / 180
        x = r * np.sin(theta) * np.cos(phi)
        y = r * np.sin(theta) * np.sin(phi)
        z = r * np.cos(theta)
        return [x, y, z]

    @staticmethod
    def cartesian_to_spherical(xyz):
        # takes list xyz (single coordinate)
        x = xyz[0]
        y = xyz[1]
        z = xyz[2]
        r = np.sqrt(x * x + y * y + z * z)
        theta = np.arccos(z / r) * 180 / np.pi  # to degrees
        phi = np.arctan2(y, x) * 180 / np.pi
        return [r, theta, phi]
