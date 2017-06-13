import xml.etree.ElementTree
import numpy as np


class IDFParser:
    def __init__(self, idf_filename):
        self.filename = idf_filename
        self.root = xml.etree.ElementTree.parse(idf_filename).getroot()
        self.ns = {'d': 'http://www.mantidproject.org/IDF/1.0'}
        # Our root should be the instrument
        assert (self.root.tag == '{' + self.ns['d'] + '}instrument')

    def get_instrument_name(self):
        """
        Returns the name of the instrument

        :return: Instrument name
        """
        return self.root.get('name')

    def get_source_name(self):
        """
        Returns the name of the source or None if no source is found

        :return: Source name or None if not found
        """
        for xml_type in self.root.findall('d:type', self.ns):
            if xml_type.get('is') == 'Source':
                return xml_type.get('name')
        return None

    def get_sample_position(self):
        """
        Find the sample position as an x,y,z coord list

        :return: The sample position as a list
        """
        for xml_type in self.root.findall('d:type', self.ns):
            if xml_type.get('is') == 'SamplePos':
                for xml_sample_component in self.root.findall('d:component', self.ns):
                    if xml_sample_component.get('type') == xml_type.get('name'):
                        location_type = xml_sample_component.find('d:location', self.ns)
                        return self.__get_vector(location_type)
        return None

    def get_rectangular_detectors(self):
        """
        Get detector banks information from a Mantid IDF file for RectangularDetector panels

        :returns A generator which yields details of each detector bank found in the instrument file 
        """
        # Look for detector bank definition
        detector_number = 0
        for xml_type in self.root.findall('d:type', self.ns):
            if xml_type.get('is') == 'rectangular_detector':
                x_pixel_size, y_pixel_size, thickness = self.__get_pixel_shape(self.root, xml_type.get('type'))
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

    def __get_vector(self, xml_point):
        return np.array([self.__none_to_zero(xml_point.get('x')),
                         self.__none_to_zero(xml_point.get('y')),
                         self.__none_to_zero(xml_point.get('z'))]).astype(float)

    def __get_pixel_names_and_shapes(self):
        pixels = []
        for xml_type in self.root.findall('d:type', self.ns):
            if xml_type.get('is') == 'detector':
                name = xml_type.get('name')
                pixels.append({'name': name, 'shape': self.__get_shape(xml_type)})
        return pixels

    def __get_detector_offsets(self, xml_type):
        """
        Gets list of locations from a detector component

        :param xml_type: Component of a detector containing location or locations elements
        :return: List of locations for this component
        """
        detector_offsets = []
        for child in xml_type:
            if child.tag == '{' + self.ns['d'] + '}location':
                detector_offsets.append(self.__get_vector(child))
            elif child.tag == '{' + self.ns['d'] + '}locations':
                for axis_number, axis in enumerate(['x', 'y', 'z']):
                    if child.get(axis):
                        for location in np.linspace(start=float(child.get(axis)),
                                                    stop=float(child.get(axis + '-end')),
                                                    num=int(child.get('n-elements'))):
                            location_vector = np.array([0.0, 0.0, 0.0]).astype(float)
                            location_vector[axis_number] = location
                            detector_offsets.append(location_vector)
                        break
        return detector_offsets

    def get_detectors(self):
        """
        WIP
        Will return full details for high level detector components (for example detector banks/panels) which are not
        described using RectangularDetector or StructuredDetector in the IDF

        :return:
        """
        raise NotImplementedError
        pixels = self.__get_pixel_names_and_shapes()
        detectors = []
        for pixel in pixels:
            detector_name = pixel['name']
            offsets = []
            smallest_component_names = []
            for xml_type in self.root.findall('d:type', self.ns):
                for smallest_component in xml_type.findall('d:component', self.ns):
                    if smallest_component.get('type') == detector_name:
                        if smallest_component.get('is') in ['StructuredDetector', 'RectangularDetector']:
                            continue
                        smallest_component_names.append(xml_type.get('name'))
                        offsets.append(self.__get_detector_offsets(smallest_component))
                        self.__parse_detector_component(smallest_component_names, detectors, pixel, offsets)

    def __parse_detector_component(self, smaller_component_names, detectors, pixel, offsets):
        if smaller_component_names:
            for xml_type in self.root.findall('d:type', self.ns):
                for component in xml_type.findall('d:component', self.ns):
                    if component.get('type') in smaller_component_names:
                        if component.get('is') in ['StructuredDetector', 'RectangularDetector']:
                            continue
                        larger_component_name = xml_type.get('name')
                        offsets.append(self.__get_detector_offsets(component))
                        self.__parse_detector_component(larger_component_name, detectors, pixel, offsets)
                        return
            self.__check_for_top_level_detector_component(smaller_component_names, detectors, pixel, offsets)

    def __check_for_top_level_detector_component(self, smaller_component_names, detectors, pixel, offsets):
        for component in self.root.findall('d:component', self.ns):
            if component.get('type') in smaller_component_names:
                idlist = component.get('idlist')
                name = component.get('name')
                if idlist:
                    # TODO get ids and add them to the detector dictionary
                    location_type = component.find('d:location', self.ns)
                    location = self.__get_vector(location_type)
                    facing_type = location_type.find('d:facing', self.ns)
                    if facing_type:
                        # Should add an orientation field to the detector for rotating to achieve facing
                        raise NotImplementedError('Dealing with "facing" elements is not yet implemented.')
                    detectors.append({'name': name, 'pixel': pixel, 'offsets': offsets, 'location': location})
                else:
                    raise Exception('Found a top level detector component with no idlist, name: ' + name)

    def __get_pixel_shape(self, xml_root, type_name):
        for xml_type in xml_root.findall('d:type', self.ns):
            if xml_type.get('name') == type_name and xml_type.get('is') == 'detector':
                return self.__get_shape(xml_type)
        return None

    def __get_shape(self, xml_type):
        cuboid = xml_type.find('d:cuboid', self.ns)
        cylinder = xml_type.find('d:cylinder', self.ns)
        if cuboid is not None:
            return self.__parse_cuboid(cuboid)
        elif cylinder is not None:
            return self.__parse_cylinder(cylinder)
        else:
            raise Exception('pixel is not of known shape')

    def __parse_cuboid(self, cuboid_xml):
        """
        Get details NeXus needs to describe a cuboid

        :param cuboid_xml: The xml element describing the cuboid
        :return: A dictionary containing dimensions of the cuboid
        """
        left_front_bottom = self.__get_vector(cuboid_xml.find('d:left-front-bottom-point', self.ns))
        left_front_top = self.__get_vector(cuboid_xml.find('d:left-front-top-point', self.ns))
        left_back_bottom = self.__get_vector(cuboid_xml.find('d:left-back-bottom-point', self.ns))
        right_front_bottom = self.__get_vector(cuboid_xml.find('d:right-front-bottom-point', self.ns))
        # Assume x pixel size is left to right
        left_to_right = right_front_bottom - left_front_bottom
        x_pixel_size = np.sqrt(np.dot(left_to_right, left_to_right))
        # Assume y pixel size is front to back
        front_to_back = left_back_bottom - left_front_bottom
        y_pixel_size = np.sqrt(np.dot(front_to_back, front_to_back))
        # Assume thickness is top to bottom
        top_to_bottom = left_front_top - left_front_bottom
        thickness = np.sqrt(np.dot(top_to_bottom, top_to_bottom))
        return {'shape': 'cuboid', 'x_pixel_size': x_pixel_size, 'y_pixel_size': y_pixel_size, 'thickness': thickness}

    def __parse_cylinder(self, cylinder_xml):
        """
        Get details NeXus needs to describe a cylinder

        :param cylinder_xml: The xml element describing the cylinder
        :return: A dictionary containing dimensions of the cylinder
        """
        axis = self.__get_vector(cylinder_xml.find('d:axis', self.ns))
        radius = float(cylinder_xml.find('d:radius', self.ns).get('val'))
        height = float(cylinder_xml.find('d:height', self.ns).get('val'))
        # Check axis is only finite in x or y as we only have x_pixel_size and y_pixel_size to
        # put the height in for NeXus, otherwise throw error
        if (int(axis[0] != 0) + int(axis[1] != 0)) != 1 or axis[2] != 0:
            raise Exception(
                'Cylinder found with axis not aligned with x or y axis. This cannot be represented in NeXus standard.')
        x_pixel_size = None
        y_pixel_size = None
        if axis[0] != 0:
            x_pixel_size = height
        else:
            y_pixel_size = height
        return {'shape': 'cylinder', 'x_pixel_size': x_pixel_size, 'y_pixel_size': y_pixel_size,
                'diameter': 2.0 * radius}

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
                    location = {'x': location_type.get('x'), 'y': location_type.get('y'),
                                'z': location_type.get('z')}
                    angle = location_type.get('rot')
                    if angle is not None:
                        rotation = {'angle': location_type.get('rot'), 'axis_x': location_type.get('axis-x'),
                                    'axis_y': location_type.get('axis-y'),
                                    'axis_z': location_type.get('axis-z')}
                    else:
                        rotation = None
                yield {'id_start': int(xml_type.get('idstart')), 'X_id_step': int(xml_type.get('idstepbyrow')),
                       'Y_id_step': int(xml_type.get('idstep')), 'name': xml_type.get('name'),
                       'type_name': xml_type.get('type'), 'location': location,
                       'rotation': rotation}

    def get_monitors(self):
        all_monitor_type_names, monitor_types = self.__get_monitor_types()
        # Now look for components with one of these types, they'll be grouped in another element
        # Add them to a list, NB order matters for id assignment
        monitors = []
        for xml_type in self.root.findall('d:type', self.ns):
            for xml_component in xml_type.findall('d:component', self.ns):
                type_name = xml_component.get('type')
                if type_name in all_monitor_type_names:
                    for xml_location in xml_component.findall('d:location', self.ns):
                        monitors.append({'name': xml_location.get('name'), 'location': self.__get_vector(xml_location),
                                         'type_name': type_name, 'id': None})
                    id_list = self.__get_monitor_idlist(xml_type.get('name'))
                    self.__assign_ids(monitors, id_list)
        return monitors, monitor_types

    @staticmethod
    def __assign_ids(components, id_list):
        """
        Assign an id from id_list to each id-less component dictionary in components list in order
        :param components: List of dictionaries, dictionary should have id key, assign an id to it if None
        :param id_list: List of ids to assign
        """
        next_id = 0
        for component in components:
            if component.id is None:
                component.id = id_list[next_id]
                next_id += 1

    def __get_monitor_idlist(self, type_name):
        idlist = []
        for xml_component in self.root.findall('d:component', self.ns):
            if xml_component.get('type') == type_name:
                location_xml = xml_component.find('d:location', self.ns)
                if location_xml:
                    if len(location_xml.attrib) > 0:
                        raise NotImplementedError(
                            'dealing with location in __get_monitor_idlist is not implemented yet')
                idlist_name = xml_component.get('idlist')
                for xml_idlist in self.root.findall('d:idlist', self.ns):
                    if xml_idlist.get('name') == idlist_name:
                        for xml_id in xml_idlist.findall('d:id', self.ns):
                            idlist = idlist + list(range(int(xml_id.get('start')), int(xml_id.get('end'))))
        return idlist

    def __get_monitor_types(self):
        monitor_types = []
        for xml_type in self.root.findall('d:type', self.ns):
            if xml_type.get('is') == 'monitor':
                name = xml_type.get('name')
                monitor_types.append({'name': name, 'shape': self.__get_shape(xml_type)})
        all_monitor_type_names = [monitor.name for monitor in monitor_types]
        return all_monitor_type_names, monitor_types

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
                    vertices[vertex_number_x, vertex_number_y, :] = self.__get_vector(vertex)
                    vertex_number_x += 1
                    if vertex_number_x > x_pixels:
                        # We've filled a row, move to the next one
                        vertex_number_x = 0
                        vertex_number_y += 1
                return vertices
        return None

    @staticmethod
    def __none_to_zero(x):
        return 0 if x is None else x
