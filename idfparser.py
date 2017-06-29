import xml.etree.ElementTree
import numpy as np
from coordinatetransformer import CoordinateTransformer
import pprint


class IDFParser:
    """
    Parses Mantid IDF files
    """

    def __init__(self, idf_file):
        """

        :param idf_file: IDF file name or object
        """
        self.root = xml.etree.ElementTree.parse(idf_file).getroot()
        self.ns = {'d': 'http://www.mantidproject.org/IDF/1.0'}
        self.__get_defaults()
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
        x = xml_point.get('x')
        y = xml_point.get('y')
        z = xml_point.get('z')
        if [x, y, z] == [None, None, None]:
            # No cartesian axes, maybe there are spherical?
            r = xml_point.get('r')
            t = xml_point.get('t')
            p = xml_point.get('p')
            vector = np.array([self.__none_to_zero(r),
                               self.__none_to_zero(t),
                               self.__none_to_zero(p)]).astype(float)
            vector = self.transform.spherical_to_cartesian(vector)
        else:
            vector = np.array([self.__none_to_zero(x),
                               self.__none_to_zero(y),
                               self.__none_to_zero(z)]).astype(float)

        return self.transform.get_nexus_coordinates(vector)

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
        pixels = self.__get_pixel_names_and_shapes()  # {'name': str, 'shape': shape_info_dict}
        types = []  # {'name': str, 'subcomponents':[str]}
        components = []  # {'type': str, 'offsets':[[int]]}
        # detectors = []  # top-level components {'name':str, 'type':str, idlist:[[int]], location: [float]}
        for pixel in pixels:
            self.__collect_detector_components(types, components, pixel['name'])

        detectors = self.__collect_top_level_detector_components([instr_type['name'] for instr_type in types])

        # Collate info for detector_modules
        detector_modules = self.__collate_detector_module_info(types, components,
                                                               self.__find_detector_module_names(types))
        self.pprint_things((pixels, types, components, detectors))

        if detector_modules:
            pass
        else:
            raise NotImplementedError('Case of no detector_modules in the detector is not yet implemented')

    @staticmethod
    def __find_detector_module_names(types):
        def get_det_module_names():
            for instr_type in types:
                if len(instr_type['subcomponents']) > 1:
                    for subcomponent in instr_type['subcomponents']:
                        yield subcomponent

        return list(get_det_module_names())

    def __collate_detector_module_info(self, types, components, detector_module_names):
        detector_modules = []  # {'name': str, 'offsets':[[float]], 'pixel_name':str}
        for det_type_name in detector_module_names:
            type_chain = []
            while True:
                type_chain.insert(0, det_type_name)
                det_type = \
                    next((detector_type for detector_type in types if detector_type["name"] == det_type_name), None)
                if det_type is not None:
                    if len(det_type['subcomponents']) != 1:
                        raise Exception(
                            'Expected to find single subcomponent  in IDFParser.__collate_detector_module_info')
                    det_type_name = det_type['subcomponents'][0]
                else:
                    break

            pixel_name = type_chain[0]
            offsets = next((component for component in components if component["type"] == pixel_name), None)[
                'offsets']
            for component_type in type_chain[1:]:
                new_offsets = \
                    next((component for component in components if component["type"] == component_type), None)[
                        'offsets']
                offsets = self.__calculate_new_offsets(offsets, new_offsets)
            detector_modules.append({'name': det_type_name, 'pixel_name': pixel_name, 'offsets': offsets})
        return detector_modules

    @staticmethod
    def __calculate_new_offsets(old_offsets, new_offsets):
        offsets = []
        for old_offset in old_offsets:
            # apply as a translation to each new offset
            for new_offset in new_offsets:
                offsets.append(np.add(old_offset, new_offset))
        return offsets

    @staticmethod
    def pprint_things(things):
        pp = pprint.PrettyPrinter(indent=4)
        for thing in things:
            pp.pprint(thing)

    def __collect_detector_components(self, types, components, search_type):
        for xml_type in self.root.findall('d:type', self.ns):
            for xml_component in xml_type.findall('d:component', self.ns):
                if xml_component.get('type') == search_type:
                    offsets = self.__get_detector_offsets(xml_component)
                    components.append({'type': search_type, 'offsets': offsets})
                    self.__add_component_to_type(types, xml_type.get('name'), search_type)
                    self.__collect_detector_components(types, components, xml_type.get('name'))

    @staticmethod
    def __add_component_to_type(types, type_name, component_type):
        """
        If there is a type with type_name already in types then append component_type to its subcomponents
        otherwise add the type with subcomponent

        :param types: list of dictionary describing each type
        :param type_name: the name of the type which has a subcomponent of component_type
        :param component_type: name of the type of the subcomponent
        :return:
        """
        det_type = next((detector_type for detector_type in types if detector_type["name"] == type_name), None)
        if det_type is not None:
            det_type['subcomponents'].append(component_type)
        else:
            types.append({'name': type_name, 'subcomponents': [component_type]})

    def __collect_top_level_detector_components(self, smaller_type_names):
        detectors = []
        for component in self.root.findall('d:component', self.ns):
            if component.get('type') in smaller_type_names:
                idlist = component.get('idlist')
                name = component.get('name')
                if idlist:
                    location_type = component.find('d:location', self.ns)
                    location = self.__get_vector(location_type)
                    facing_type = location_type.find('d:facing', self.ns)
                    if facing_type:
                        # Should add an orientation field to the detector for rotating to achieve facing
                        raise NotImplementedError('Dealing with "facing" elements is not yet implemented.')
                    detectors.append({'name': name, 'type': component.get('type'), 'location': location,
                                      'idlist': component.get('idlist')})
                else:
                    raise Exception('Found a top level detector component with no idlist, name: ' + name)
        return detectors

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
            if len(list(xml_type)) != 0:
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
        if (int(axis[0] != 0) + int(axis[1] != 0) + int(axis[2] != 0)) != 1:
            raise Exception(
                'Cylinder axis must be aligned with a cartesian axis, '
                'otherwise it cannot be represented in NeXus standard.')
        x_pixel_size = None
        y_pixel_size = None
        z_pixel_size = None
        if axis[0] != 0:
            x_pixel_size = height
        elif axis[1] != 0:
            y_pixel_size = height
        else:
            z_pixel_size = height
        return {'shape': 'cylinder', 'x_pixel_size': x_pixel_size, 'y_pixel_size': y_pixel_size,
                'thickness': z_pixel_size, 'diameter': 2.0 * radius}

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
            type_contains_monitors = False
            for xml_component in xml_type.findall('d:component', self.ns):
                type_name = xml_component.get('type')
                if type_name in all_monitor_type_names:
                    type_contains_monitors = True
                    for xml_location in xml_component.findall('d:location', self.ns):
                        monitors.append({'name': xml_location.get('name'), 'location': self.__get_vector(xml_location),
                                         'type_name': type_name, 'id': None})
            if type_contains_monitors:
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
            if component['id'] is None:
                component['id'] = id_list[next_id]
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
                    if xml_idlist.get('idname') == idlist_name:
                        for xml_id in xml_idlist.findall('d:id', self.ns):
                            idlist = idlist + list(range(int(xml_id.get('start')), int(xml_id.get('end')) + 1))
        return idlist

    def __get_monitor_types(self):
        monitor_types = []
        for xml_type in self.root.findall('d:type', self.ns):
            if xml_type.get('is') == 'monitor':
                name = xml_type.get('name')
                monitor_types.append({'name': name, 'shape': self.__get_shape(xml_type)})
        all_monitor_type_names = [monitor['name'] for monitor in monitor_types]
        return all_monitor_type_names, monitor_types

    def __get_defaults(self):
        angle_units = self.__get_default_units()
        self.__get_default_coord_systems(angle_units)

    def __get_default_coord_systems(self, angle_units):
        xml_defaults = self.root.find('d:defaults', self.ns)
        nexus_x = 'x'
        nexus_y = 'y'
        nexus_z = 'z'
        if xml_defaults:
            # Default "location" element is undocumented in
            # http://docs.mantidproject.org/nightly/concepts/InstrumentDefinitionFile.html
            # but it seems to define the zero axis for the spherical coordinate system
            xml_coord_map = xml_defaults.find('d:location', self.ns)
            if xml_coord_map:
                if not [float(xml_coord_map.get('r')), float(xml_coord_map.get('t')), float(xml_coord_map.get('p')),
                        float(xml_coord_map.get('ang')), float(xml_coord_map.get('x')), float(xml_coord_map.get('y')),
                        float(xml_coord_map.get('z'))] == [0, 0, 0, 0, 0, 0, 1]:
                    raise NotImplementedError('Dealing with spherical coordinate systems where the zero'
                                              'axis is not along the z axis is not yet implemented')
            xml_ref_frame = xml_defaults.find('d:reference-frame', self.ns)
            xml_along_beam = xml_ref_frame.find('d:along-beam', self.ns)
            xml_up = xml_ref_frame.find('d:pointing-up', self.ns)
            if xml_along_beam is None or xml_up is None:
                raise Exception('Expected "along-beam" and "pointing-up" to be specified '
                                'in the default reference frame in the IDF')
            nexus_y = xml_up.get('axis')
            nexus_z = xml_along_beam.get('axis')
            handedness = 'right'
            xml_handedness = xml_ref_frame.find('d:handedness', self.ns)
            if xml_handedness:
                handedness = xml_handedness.get('val')

            def is_negative(direction):
                return direction[0] == '-'

            def flip_axis(nexus_a):
                return '-' + nexus_a if not is_negative(nexus_a) else nexus_a[1:]

            unsigned_yz_list = [nexus_y[1:] if is_negative(nexus_y) else nexus_y,
                                nexus_z[1:] if is_negative(nexus_z) else nexus_z]

            # Assuming right-handedness
            if unsigned_yz_list == ['y', 'z']:
                nexus_x = 'x'
            elif unsigned_yz_list == ['z', 'y']:
                nexus_x = '-x'
            elif unsigned_yz_list == ['x', 'y']:
                nexus_x = '-z'
            elif unsigned_yz_list == ['y', 'x']:
                nexus_x = 'z'
            elif unsigned_yz_list == ['x', 'z']:
                nexus_x = 'y'
            elif unsigned_yz_list == ['z', 'x']:
                nexus_x = '-y'
            else:
                raise RuntimeError('Unexpected yz list in IDFParser.__get_default_coord_systems')

            if is_negative(nexus_y) ^ is_negative(nexus_z):
                nexus_x = flip_axis(nexus_x)

            if handedness == 'left':
                nexus_x = flip_axis(nexus_x)

        self.transform = CoordinateTransformer(angles_in_degrees=(angle_units == 'deg'),
                                               nexus_coords=[nexus_x, nexus_y, nexus_z])

    def __get_default_units(self):
        self.length_units = 'm'
        self.angle_units = 'deg'

        xml_defaults = self.root.find('d:defaults', self.ns)
        if xml_defaults:
            xml_default_length = xml_defaults.find('d:length', self.ns)
            idf_length_units = xml_default_length.get('unit')
            # Prefer SI unit abbreviation if we can
            if idf_length_units.lower() in ['meter', 'metre', 'meters', 'metres', 'm']:
                self.length_units = 'm'
            else:
                self.length_units = idf_length_units
            xml_default_angle = xml_defaults.find('d:angle', self.ns)
            idf_angle_units = xml_default_angle.get('unit')
            if idf_angle_units.lower() in ['deg', 'degree', 'degrees']:
                self.angle_units = 'deg'
            elif idf_angle_units.lower() in ['rad', 'radian', 'radians']:
                self.angle_units = 'rad'
            else:
                raise ValueError('Unexpected default unit for angles in IDF file')
        return self.angle_units

    def get_length_units(self):
        return self.length_units

    def get_angle_units(self):
        return self.angle_units

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
