import xml.etree.ElementTree
import numpy as np


class IDFParser:
    def __init__(self, idf_filename):
        self.root = xml.etree.ElementTree.parse(idf_filename).getroot()
        self.ns = {'d': 'http://www.mantidproject.org/IDF/1.0'}
        # Our root should be the instrument
        assert (self.root.tag == '{' + self.ns['d'] + '}instrument')

    def get_detector_banks(self):
        """
        Get detector banks information from a Mantid IDF file
        NB, currently only works for "RectangularDetector" panels

        :returns A generator which yields details of each detector bank found in the instrument file 
        """
        # Look for detector bank definition
        detector_number = 0
        for xml_type in self.root.findall('d:type', self.ns):
            if xml_type.get('is') == 'rectangular_detector':
                x_pixel_size, y_pixel_size, thickness = self.__get_pixel(self.root, xml_type.get('type'))
                bank_type_name = xml_type.get('name')
                x_pixel_offset_1d = self.__get_1d_pixel_offsets('x', xml_type)
                y_pixel_offset_1d = self.__get_1d_pixel_offsets('y', xml_type)
                x_pixel_offset, y_pixel_offset = np.meshgrid(x_pixel_offset_1d, y_pixel_offset_1d)
                for component in self.root.findall('d:component', self.ns):
                    if component.get('type') == bank_type_name:
                        detector_number += 1
                        det_bank_info = {'name': component.find('d:location', self.ns).get('name'),
                                         'number': detector_number,
                                         'x_pixel_size': x_pixel_size,
                                         'y_pixel_size': y_pixel_size,
                                         'thickness': thickness,
                                         'x_pixel_offset': x_pixel_offset,
                                         'y_pixel_offset': y_pixel_offset}
                        # TODO also get the pixel id information (detector_number)
                        location = component.find('d:location', self.ns)
                        distance_list = np.array([location.get('x'), location.get('y'), location.get('z')])
                        # If any of these are omitted it means position 0 on that axis
                        det_bank_info['distance'] = np.array(
                            map(lambda x: 0 if x is None else x, distance_list)).astype(float)
                        yield det_bank_info

    @staticmethod
    def __get_point(xml_point):
        return np.array([xml_point.get('x'), xml_point.get('y'), xml_point.get('z')]).astype(float)

    def __get_pixel(self, xml_root, type_name):
        ns = {'d': 'http://www.mantidproject.org/IDF/1.0'}
        for xml_type in xml_root.findall('d:type', ns):
            if xml_type.get('name') == type_name and xml_type.get('is') == 'detector':
                cuboid = xml_type.find('d:cuboid', ns)
                if cuboid is not None:
                    left_front_bottom = self.__get_point(cuboid.find('d:left-front-bottom-point', ns))
                    left_front_top = self.__get_point(cuboid.find('d:left-front-top-point', ns))
                    left_back_bottom = self.__get_point(cuboid.find('d:left-back-bottom-point', ns))
                    right_front_bottom = self.__get_point(cuboid.find('d:right-front-bottom-point', ns))
                    # Assume x pixel size is left to right
                    left_to_right = right_front_bottom - left_front_bottom
                    x_pixel_size = np.sqrt(np.dot(left_to_right, left_to_right))
                    # Assume y pixel size is front to back
                    front_to_back = left_back_bottom - left_front_bottom
                    y_pixel_size = np.sqrt(np.dot(front_to_back, front_to_back))
                    # Assume thickness is top to bottom
                    top_to_bottom = left_front_top - left_front_bottom
                    thickness = np.sqrt(np.dot(top_to_bottom, top_to_bottom))
                    return x_pixel_size, y_pixel_size, thickness
                else:
                    print('no cuboid shape found to define pixel')
        return None, None, None

    @staticmethod
    def __get_1d_pixel_offsets(dimension_name, xml_type):
        step = float(xml_type.get(dimension_name + 'step'))
        pixels = int(xml_type.get(dimension_name + 'pixels'))
        start = float(xml_type.get(dimension_name + 'start'))
        stop = start + (step * pixels)
        return np.linspace(start, stop, pixels)
