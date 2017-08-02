import xml.etree.ElementTree
import numpy as np
from coordinatetransformer import CoordinateTransformer
import logging
import nexusutils
import itertools
import uuid

logger = logging.getLogger('NeXus_Builder')


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
                        location = self.__get_vector(location_type)
                        if location is not None:
                            return location
                        else:
                            return np.array([0.0, 0.0, 0.0])
        raise Exception('SamplePos tag not found in IDF')

    def get_rectangular_detectors(self):
        """
        Get detector banks information from a Mantid IDF file for RectangularDetector panels

        :returns A generator which yields details of each detector bank found in the instrument file 
        """
        # Look for detector bank definition
        for xml_type in self.root.findall('d:type', self.ns):
            if xml_type.get('is') == 'rectangular_detector':
                pixel_name = xml_type.get('type')
                pixel_shape = self.__get_pixel_shape(self.root, pixel_name)
                bank_type_name = xml_type.get('name')
                x_pixel_offset_1d = self.__get_1d_pixel_offsets('x', xml_type)
                y_pixel_offset_1d = self.__get_1d_pixel_offsets('y', xml_type)
                x_pixel_offset, y_pixel_offset = np.meshgrid(x_pixel_offset_1d, y_pixel_offset_1d)
                z_pixel_offset = np.zeros_like(x_pixel_offset)
                offsets = np.stack((x_pixel_offset, y_pixel_offset, z_pixel_offset), axis=-1)
                for component in self.root.findall('d:component', self.ns):
                    if component.get('type') == bank_type_name:
                        location = component.find('d:location', self.ns)
                        detector_numbers = self.__get_rectangular_detector_ids(component, len(x_pixel_offset),
                                                                               len(y_pixel_offset))
                        detector_name = component.find('d:location', self.ns).get('name')
                        if detector_name is None:
                            detector_name = bank_type_name
                        det_bank_info = {'name': detector_name,
                                         'pixel': {'name': pixel_name, 'shape': pixel_shape},
                                         'offsets': offsets,
                                         'idlist': detector_numbers,
                                         'sub_components': [bank_type_name],  # allows use of links in builder
                                         'location': self.__get_vector(location),
                                         'orientation': self.__parse_facing_element(component)}
                        yield det_bank_info

    @staticmethod
    def __get_rectangular_detector_ids(component, x_pixels, y_pixels):
        idstart = int(component.get('idstart'))
        idstep = int(component.get('idstep'))
        idfillbyfirst = component.get('idfillbyfirst')
        idstepbyrow = int(component.get('idstepbyrow'))
        if idfillbyfirst == 'x':
            x_2d, y_2d = np.mgrid[0:x_pixels * idstep:idstep,
                                  0:y_pixels * idstepbyrow:idstepbyrow]
        else:
            x_2d, y_2d = np.mgrid[0:x_pixels * idstepbyrow:idstepbyrow,
                                  0:y_pixels * idstep:idstep]
        return (x_2d + y_2d) + idstart

    def __get_vector(self, xml_point):
        x = xml_point.get('x')
        y = xml_point.get('y')
        z = xml_point.get('z')
        if [x, y, z] == [None, None, None]:
            # No cartesian axes, maybe there are spherical?
            r = xml_point.get('r')
            t = xml_point.get('t')
            p = xml_point.get('p')
            if [r, t, p] == [None, None, None]:
                logger.debug('No x,y,z or r,t,p values found in IDFParser.__get_vector')
                return None
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
        """
        Get detector information from the IDF

        :return: List of detector dictionaries
        """
        pixels = self.__get_pixel_names_and_shapes()
        components = []
        for pixel in pixels:
            searched_already = list()
            self.__collect_detector_components(components, pixel['name'], searched_already)

        top_level_detector_names = self.__find_top_level_detector_names(components)
        self.__fix_top_level_components(components, top_level_detector_names)
        detectors = self.__collate_detector_info(pixels, components, top_level_detector_names)

        return detectors

    @staticmethod
    def __fix_top_level_components(components, top_level_detector_names):
        """
        For some reason IDFs often have a superfluous top level component which only links the detector to an idlist
        and does not contain a location element. Here we combine the top level component with its subcomponent to
        create a new top level component with all the necessary metadata.
        """
        delete_components = []
        for component in components:
            if component['name'] in top_level_detector_names:
                if component['locations'][0][0] is None:
                    # We'll have to combine this with its subcomponent
                    if len(component['sub_components']) != 1:
                        raise Exception('Top level detector component has no location defined and does not have one '
                                        'sub component to use the location of.')
                    subcomponent_name = component['sub_components'][0]
                    subcomponent = next(
                        (component for component in components if component["name"] == subcomponent_name),
                        None)
                    top_level_detector_names.add(subcomponent_name)
                    top_level_detector_names.remove(component['name'])
                    subcomponent['idlist'] = component['idlist']
                    delete_components.append(component['name'])
                    if subcomponent['locations'][0][0] is None:
                        subcomponent['locations'][0][0] = np.array([0., 0., 0.])
        components[:] = [component for component in components if not component['name'] in delete_components]

    def __collate_detector_info(self, pixels, components, top_level_detector_names):
        detectors = list()
        # Components where we don't need to calculate offsets or we have already calculated the offsets
        pixel_names = {pixel['name'] for pixel in pixels}
        component_names_offsets_known = set(pixel_names)
        all_component_names = {component['name'] for component in components}
        all_component_names.update(component_names_offsets_known)
        while component_names_offsets_known != all_component_names:
            # Propagate pixel name up through components too,
            # if we get a component with multiple pixel types then raise an error,
            # eventually can deal with this by creating NXdetector_modules.
            for component in components:
                # If we know the offsets of all of this component's sub-components
                # then we can calculate the offsets for it.
                sub_component_names = component['sub_components']
                if set(sub_component_names).issubset(component_names_offsets_known):
                    # Get offset lists of the sub components
                    sub_component_offsets = []
                    for sub_comp_index, sub_component_name in enumerate(sub_component_names):
                        if sub_component_name in pixel_names:
                            sub_component_offsets.append([np.array([0.0, 0.0, 0.0])])
                            component['pixels'].append(sub_component_name)
                        else:
                            component['pixels'].extend(self.__get_component_pixels(components, sub_component_name))
                            sub_component_offsets.append(self.__get_component_offsets(components, sub_component_name))
                    if not self.__all_elements_equal(component['pixels']):
                        raise NotImplementedError(component['name'] +
                                                  ' has multiple pixel types, need to implement treating '
                                                  'its sub-components as NXdetector_modules')
                    if component['name'] in top_level_detector_names:
                        component['offsets'] = list(itertools.chain.from_iterable(sub_component_offsets))
                        pixel_name = component['pixels'][0]
                        pixel = next((pixel for pixel in pixels if pixel["name"] == pixel_name), None)
                        component['pixel'] = pixel
                        component['location'] = component['locations'][0][0]
                        detectors.append(component)
                    else:
                        component['offsets'] = []
                        for sub_comp_index, offset_list in enumerate(sub_component_offsets):
                            component['offsets'].extend(
                                self.__calculate_new_offsets(offset_list, component['locations'][sub_comp_index]))
                    component_names_offsets_known.add(component['name'])

        return detectors

    @staticmethod
    def __all_elements_equal(input_list):
        """
        Check all elements of the input list are equal

        :param input_list: List, are all its elements equal?
        :return: Bool result
        """
        return input_list.count(input_list[0]) == len(input_list)

    @staticmethod
    def __get_component_offsets(components, component_name):
        locations = \
            next((component['offsets'] for component in components if component["name"] == component_name), None)
        return locations

    @staticmethod
    def __get_component_pixels(components, component_name):
        pixel = \
            next((component['pixels'] for component in components if component["name"] == component_name), None)
        return pixel

    def __get_id_list(self, idname):
        idlist = []
        for xml_idlist in self.root.findall('d:idlist', self.ns):
            if xml_idlist.get('idname') == idname:
                for xml_id in xml_idlist.findall('d:id', self.ns):
                    if xml_id.get('start') is not None:
                        idlist += list(range(int(xml_id.get('start')), int(xml_id.get('end')) + 1))
                    elif xml_id.get('val') is not None:
                        idlist.append(int(xml_id.get('val')))
                    else:
                        raise Exception('Could not find IDs in idlist called "' + idname + '"')
        return idlist

    @staticmethod
    def __find_top_level_detector_names(components):
        sub_component_names = set()
        component_names = set()
        for component in components:
            component_names.add(component['name'])
            for sub_component in component['sub_components']:
                sub_component_names.add(sub_component)

        # Component in component_names but not in sub_component names is a top level detector component
        top_level_detector_component_names = component_names - sub_component_names
        return top_level_detector_component_names

    @staticmethod
    def __calculate_new_offsets(old_offsets, new_offsets):
        offsets = []
        for new_offset in new_offsets:
            # apply as a translation to each old offset
            offsets.extend(old_offsets + np.expand_dims(new_offset, 1).T)
        return offsets

    def __collect_detector_components(self, components, search_type, searched_already):
        if search_type in searched_already:
            return
        searched_already.append(search_type)
        for xml_type in self.root.findall('d:type', self.ns):
            for xml_component in xml_type.findall('d:component', self.ns):
                if xml_component.get('type') == search_type:
                    name = xml_type.get('name')
                    self.__append_component(name, xml_component, components, search_type, searched_already)
        for xml_top_component in self.root.findall('d:component', self.ns):
            if xml_top_component.get('type') == search_type:
                name = xml_top_component.get('name')
                if name is None:
                    name = uuid.uuid4()
                self.__append_component(name, xml_top_component, components, search_type, searched_already)

    def __append_component(self, name, xml_component, components, search_type, searched_already):
        offsets = self.__get_detector_offsets(xml_component)
        component = next((component for component in components if component['name'] == name), None)
        if component is not None:
            component['sub_components'].append(search_type)
            idlist = xml_component.get('idlist')
            if idlist is not None:
                component['idlist'] = idlist
            component['locations'].append(offsets)
        else:
            idlist = xml_component.get('idlist')
            if idlist is not None:
                orientation = self.__parse_facing_element(xml_component)
                components.append(
                    {'name': name, 'sub_components': [search_type], 'locations': [offsets],
                     'idlist': self.__get_id_list(idlist), 'orientation': orientation, 'pixels': []})
            else:
                orientation = self.__parse_facing_element(xml_component)
                components.append(
                    {'name': name, 'sub_components': [search_type], 'locations': [offsets], 'orientation': orientation,
                     'pixels': []})
        self.__collect_detector_components(components, name, searched_already)

    def __parse_facing_element(self, xml_component):
        location_type = xml_component.find('d:location', self.ns)
        orientation = None
        if location_type is not None:
            location = self.__get_vector(location_type)
            facing_type = location_type.find('d:facing', self.ns)
            if facing_type is not None:
                facing_point = self.__get_vector(facing_type)
                vector_to_face_point = facing_point - location
                axis, angle = nexusutils.find_rotation_axis_and_angle_between_vectors(vector_to_face_point,
                                                                                      np.array([0, 0, -1.0]))
                orientation = {'axis': axis, 'angle': np.rad2deg(angle)}
        return orientation

    def __get_pixel_shape(self, xml_root, type_name):
        for xml_type in xml_root.findall('d:type', self.ns):
            if xml_type.get('name') == type_name and \
                    (xml_type.get('is') == 'detector' or xml_type.get('is') == 'Detector'):
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
        axis, axis_mag = nexusutils.normalise(self.__get_vector(cylinder_xml.find('d:axis', self.ns)))
        radius = float(cylinder_xml.find('d:radius', self.ns).get('val'))
        height = float(cylinder_xml.find('d:height', self.ns).get('val'))
        return {'shape': 'cylinder', 'height': height, 'radius': radius, 'axis': axis}

    @staticmethod
    def __get_1d_pixel_offsets(dimension_name, xml_type):
        step = float(xml_type.get(dimension_name + 'step'))
        pixels = int(xml_type.get(dimension_name + 'pixels'))
        start = float(xml_type.get(dimension_name + 'start'))
        stop = start + (step * (pixels - 1))
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
                    location = self.__get_vector(location_type)
                    angle = location_type.get('rot')
                    if angle is not None:
                        rotation = {'angle': float(location_type.get('rot')),
                                    'axis': np.array([location_type.get('axis-x'), location_type.get('axis-y'),
                                                      location_type.get('axis-z')]).astype(float)}
                    else:
                        rotation = None
                yield {'id_start': int(xml_type.get('idstart')), 'X_id_step': int(xml_type.get('idstepbyrow')),
                       'Y_id_step': int(xml_type.get('idstep')), 'name': xml_type.get('name'),
                       'type_name': xml_type.get('type'), 'location': location,
                       'orientation': rotation}

    def get_monitors(self):
        """
        Get monitor information from the IDF

        :return: List of monitor dictionaries, list of monitor type names
        """
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
        for xml_component in self.root.findall('d:component', self.ns):
            if xml_component.get('type') == type_name:
                location_xml = xml_component.find('d:location', self.ns)
                if location_xml:
                    if len(location_xml.attrib) > 0:
                        raise NotImplementedError(
                            'dealing with location in __get_monitor_idlist is not implemented yet')
                idlist_name = xml_component.get('idlist')
                idlist = self.__get_id_list(idlist_name)
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
