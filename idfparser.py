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
        for xml_type in xml_root.findall('d:type', self.ns):
            if xml_type.get('name') == type_name and xml_type.get('is') == 'detector':
                cuboid = xml_type.find('d:cuboid', self.ns)
                cylinder = xml_type.find('d:cylinder', self.ns)
                if cuboid is not None:
                    return self.__parse_cuboid(cuboid)
                elif cylinder is not None:
                    return self.__parse_cylinder(cylinder)
                else:
                    print('pixel is not of known shape')
        return None, None, None

    def __parse_cuboid(self, cuboid_xml):
        left_front_bottom = self.__get_point(cuboid_xml.find('d:left-front-bottom-point', self.ns))
        left_front_top = self.__get_point(cuboid_xml.find('d:left-front-top-point', self.ns))
        left_back_bottom = self.__get_point(cuboid_xml.find('d:left-back-bottom-point', self.ns))
        right_front_bottom = self.__get_point(cuboid_xml.find('d:right-front-bottom-point', self.ns))
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

    def __parse_cylinder(self, cylinder_xml):
        # Map this geometry to x, y and z size (thickness) as best as we can

        pass

    @staticmethod
    def __get_1d_pixel_offsets(dimension_name, xml_type):
        step = float(xml_type.get(dimension_name + 'step'))
        pixels = int(xml_type.get(dimension_name + 'pixels'))
        start = float(xml_type.get(dimension_name + 'start'))
        stop = start + (step * pixels)
        return np.linspace(start, stop, pixels)

    def __get_structured_detector_typenames(self):
        names = []
        for xml_type in self.root.findall('d:type', self.ns):
            if xml_type.get('is') == 'StructuredDetector':
                names.append(xml_type.get('name'))
        return names

    def get_structured_detectors(self):
        """
        Returns details for all components which are StructuredDetectors
        :return:
        """
        structured_detector_names = self.__get_structured_detector_typenames()
        if not structured_detector_names:
            return None
        location = {}
        rotation = {}
        for xml_type in self.root.findall('d:component', self.ns):
            if xml_type.get('type') in structured_detector_names:
                for location_type in xml_type:
                    location = {'x': location_type.get('x'), 'y': location_type.get('y'), 'z': location_type.get('z')}
                    rotation = {'angle': location_type.get('rot'), 'axis_x': location_type.get('axis-x'),
                                'axis_y': location_type.get('axis-y'), 'axis_z': location_type.get('axis-z')}
                yield {'id_start': xml_type.get('idstart'), 'X_id_step': xml_type.get('idstepbyrow'),
                       'Y_id_step': xml_type.get('idstep'), 'name': xml_type.get('name'),
                       'type_name': xml_type.get('type'), 'location': location,
                       'rotation': rotation}

    def get_structured_detector_vertices(self, type_name):
        """
        Looks for type definition for a StructuredDetector with the specified name and returns an array of vertices

        :param type_name: The name of a StructuredDetector type definition
        :return: Numpy array of vertex coordinates
        """
        for xml_type in self.root.findall('d:type', self.ns):
            if xml_type.get('name') == type_name:
                x_pixels = int(xml_type.get('xpixels'))
                y_pixels = int(xml_type.get('ypixels'))
                vertices = np.zeros((x_pixels + 1, y_pixels + 1, 3))
                vertex_number_x = 0
                vertex_number_y = 0
                for vertex in xml_type:
                    vertices[vertex_number_x, vertex_number_y, :] = np.array(
                        [self.__none_to_zero(vertex.get('x')), self.__none_to_zero(vertex.get('y')),
                         self.__none_to_zero(vertex.get('z'))])
                    vertex_number_x += 1
                    if vertex_number_x > x_pixels:
                        # We've filled a row, move to the next one
                        vertex_number_x = 0
                        vertex_number_y += 1
                return vertices
        return None

    @staticmethod
    def __none_to_zero(x):
        if x is None:
            return 0
        else:
            return x
