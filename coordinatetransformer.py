import numpy as np


class CoordinateTransformer:
    """
    Transform between IDF and NeXus, units and coordinates
    """
    def __init__(self, angles_in_degrees=True, nexus_coords=None):
        self.angles_in_degrees = angles_in_degrees
        if nexus_coords is None:
            nexus_coords = ['x', 'y', 'z']
        self.default_coords = (nexus_coords == ['x', 'y', 'z'])
        self.nexus_coords_signs = \
            np.array([-1.0 if self.__is_negative(axis) else 1.0 for axis in nexus_coords]).astype(float)
        unsigned_nexus_coords = [coord[1:] if self.__is_negative(coord) else coord for coord in nexus_coords]
        self.nexus_coords_order = np.array([unsigned_nexus_coords.index('x'), unsigned_nexus_coords.index('y'),
                                            unsigned_nexus_coords.index('z')])

    def get_angle_in_degrees(self, angle):
        """
        Convert angle to degrees if it isn't already

        :param angle: Angle to return in degrees
        :return: Angle in degrees
        """
        return angle if self.angles_in_degrees else np.rad2deg(angle)

    def get_nexus_coordinates(self, vector):
        """
        Convert vector in the IDF coordinate system to vector in the NeXus coordinate system

        :param vector: Vector in IDF coordinate system
        :return: Vector as a numpy array in the NeXus coordinate system
        """
        vector = np.array(vector)  # Make sure vector is a numpy array
        if self.default_coords:
            return vector
        else:
            vector = np.multiply(vector, self.nexus_coords_signs)
            return vector[self.nexus_coords_order]

    @staticmethod
    def __is_negative(direction):
        """
        Return true if first charactor of direction is "-"

        :param direction: Direction is an axis string, for example "-x"
        :return: Bool true if first charactor of direction is "-"
        """
        return direction[0] == '-'

    def spherical_to_cartesian(self, rthetaphi):
        """
        Convert spherical to cartesian coordinates

        :param rthetaphi: List or array r,theta,phi (single coordinate)
        :return: List x,y,z
        """
        # takes list rthetaphi (single coordinate)
        r = rthetaphi[0]
        theta = rthetaphi[1]
        phi = rthetaphi[2]
        if self.angles_in_degrees:
            theta = np.deg2rad(theta)
            phi = np.deg2rad(phi)
        x = r * np.sin(theta) * np.cos(phi)
        y = r * np.sin(theta) * np.sin(phi)
        z = r * np.cos(theta)
        return [x, y, z]

    @staticmethod
    def cartesian_to_spherical(xyz):
        """
        Convert cartesian to spherical coordinates

        :param xyz: List or array x,y,z (single coordinate)
        :return: List r,theta,phi
        """
        # takes list xyz (single coordinate)
        x = xyz[0]
        y = xyz[1]
        z = xyz[2]
        r = np.sqrt(x * x + y * y + z * z)
        theta = np.arccos(z / r) * 180 / np.pi  # to degrees
        phi = np.arctan2(y, x) * 180 / np.pi
        return [r, theta, phi]
