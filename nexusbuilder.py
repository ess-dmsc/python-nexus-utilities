import h5py
import logging
from collections import OrderedDict
import tables
import os
import numpy as np
from idfparser import IDFParser
import nexusutils

logger = logging.getLogger('NeXus_Builder')
logger.setLevel(logging.INFO)
console = logging.StreamHandler()
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
console.setFormatter(formatter)
logger.addHandler(console)


class NexusBuilder:
    """
    Assists with building example NeXus files in prototype ESS format from existing files from other institutions

    NB. tables import looks redundant but actually loads BLOSC compression filter
    """

    def __init__(self, output_nexus_filename, input_nexus_filename=None, compress_type=None, compress_opts=None,
                 nx_entry_name='raw_data_1', idf_file=None, file_in_memory=False):
        """
        compress_type=32001 for BLOSC

        :param output_nexus_filename: Name of the output file
        :param input_nexus_filename: Name of the input file
        :param nx_entry_name: Name of the root group (NXentry class)
        :param compress_type: Name or id of compression filter https://support.hdfgroup.org/services/contributions.html
        :param compress_opts: Compression options, for example gzip compression level
        :param idf_file: File name or object for a Mantid IDF file from which to get instrument geometry
        :param file_in_memory: If true the NeXus file is built in memory and never written to disk (for testing)
        """
        self.compress_type = compress_type
        self.compress_opts = compress_opts
        if input_nexus_filename:
            self.source_file = h5py.File(input_nexus_filename, 'r')
        else:
            self.source_file = None
        if file_in_memory:
            self.target_file = h5py.File(output_nexus_filename, 'w', driver='core', backing_store=False)
        else:
            self.target_file = h5py.File(output_nexus_filename, 'w')
        # Having an NXentry root group is compulsory in NeXus format
        self.root = self.__add_nx_entry(nx_entry_name)
        if idf_file:
            self.idf_parser = IDFParser(idf_file)
            self.length_units = self.idf_parser.get_length_units()
        else:
            self.idf_parser = None
            self.length_units = 'm'
        self.instrument = None

    def get_root(self):
        return self.root

    def copy_items(self, dataset_map):
        """
        Copy datasets and groups from one NeXus file to another
        NB, the order is important as the method of copying groups used deletes any sub-groups and datasets.

        :param dataset_map: Input groups and datasets to output ones, order must be top-down in hierarchy of output file 
                            Must be ordered.
        """
        if not isinstance(dataset_map, OrderedDict):
            raise Exception(
                'Map of source and target items must be an OrderedDict in top-down hierarchy order of the target file')

        for source_item_name, target_item_name in dataset_map.items():
            source_item = self.source_file.get(source_item_name)
            if isinstance(source_item, h5py.Dataset):
                self.__copy_dataset(source_item, target_item_name)
            elif isinstance(source_item, h5py.Group):
                self.__copy_group(source_item_name, target_item_name)

    def add_user(self, name, affiliation, number=1):
        """
        Add an NXuser
        
        :param name: Name of the user 
        :param affiliation: Affiliation of the user
        :param number: User entry number, usually starting from 1
        :return: NXuser
        """
        user_group = self.add_nx_group(self.root, 'user_' + str(number), 'NXuser')
        self.add_dataset(user_group, 'name', name)
        self.add_dataset(user_group, 'affiliation', affiliation)
        return user_group

    def add_dataset(self, group, name, data, attributes=None):
        """
        Add a dataset to a given group

        :param group: Group object, or group path from NXentry as a string
        :param name: Name of the dataset to create
        :param data: Data to put in the dataset
        :param attributes: Optional dictionary of attributes to add to dataset
        :return: Dataset
        """
        if isinstance(group, str):
            group = self.root[group]

        if isinstance(data, str):
            dataset = group.create_dataset(name, data=np.array(data).astype('|S' + str(len(data))))
        elif nexusutils.is_scalar(data):
            # Don't try to use compression with scalar datasets
            dataset = group.create_dataset(name, data=data)
        else:
            dataset = group.create_dataset(name, data=data, compression=self.compress_type,
                                           compression_opts=self.compress_opts)

        if attributes:
            for key in attributes:
                if isinstance(attributes[key], str):
                    # Since python 3 we have to treat strings like this
                    dataset.attrs.create(key, np.array(attributes[key]).astype('|S' + str(len(attributes[key]))))
                else:
                    dataset.attrs.create(key, np.array(attributes[key]))
        return dataset

    def add_detectors_from_idf(self):
        """
        Add detector banks from a Mantid IDF file

        :return: Number of detector panels added
        """
        if self.idf_parser is None:
            logger.error('No IDF file was given to the NexusBuilder, cannot call add_detector_banks_from_idf')
        total_panels = 0
        detectors = self.idf_parser.get_detectors()
        detectors += list(self.idf_parser.get_rectangular_detectors())
        written_types = []  # {'types': [str], 'group': hdf5group}
        if detectors is not None:
            for detector in detectors:
                total_panels += 1
                new_detector_type = True
                pixel_shape_group = None
                if detector['sub_components'] in [written_type['types'] for written_type in written_types]:
                    new_detector_type = False
                    written_group = next((written_type['group'] for written_type in written_types if
                                          written_type['types'] == detector['sub_components']), None)
                    try:
                        z_offset_dataset = written_group['z_pixel_offset']
                    except KeyError:
                        z_offset_dataset = None
                    pixel_offsets = {'x_pixel_offset': written_group['x_pixel_offset'],
                                     'y_pixel_offset': written_group['y_pixel_offset'],
                                     'z_pixel_offset': z_offset_dataset}
                    if 'pixel_shape' in list(written_group.keys()):
                        pixel_shape_group = written_group['pixel_shape']
                else:
                    offsets = np.array(detector['offsets'])
                    pixel_offsets = {'x_pixel_offset': offsets[..., 0], 'y_pixel_offset': offsets[..., 1],
                                     'z_pixel_offset': offsets[..., 2]}
                    if np.count_nonzero(pixel_offsets['z_pixel_offset']) == 0:
                        pixel_offsets['z_pixel_offset'] = None

                pixel_shape = detector['pixel']['shape']
                if pixel_shape['shape'] == 'cuboid':
                    x_pixel_size = pixel_shape['x_pixel_size']
                    y_pixel_size = pixel_shape['y_pixel_size']
                    thickness = pixel_shape['thickness']
                else:
                    x_pixel_size = y_pixel_size = thickness = None

                detector_group = self.add_detector(detector['name'], total_panels, detector['idlist'],
                                                   pixel_offsets, x_pixel_size=x_pixel_size, y_pixel_size=y_pixel_size,
                                                   thickness=thickness)

                self.__add_detector_transformations(detector, detector_group)
                self.__add_detector_pixel_geometry(detector_group, new_detector_type, pixel_shape, pixel_shape_group)

                if new_detector_type:
                    written_types.append({'types': detector['sub_components'], 'group': detector_group})

        return total_panels

    def __add_detector_pixel_geometry(self, detector_group, new_detector_type, pixel_shape, pixel_shape_group):
        if pixel_shape['shape'] == 'cylinder':
            if new_detector_type:
                self.add_tube_pixel(detector_group, pixel_shape['height'], pixel_shape['radius'],
                                    pixel_shape['axis'])
            else:
                detector_group['pixel_shape'] = pixel_shape_group
        elif pixel_shape['shape'] != 'cuboid':
            raise NotImplementedError('Pixel shape other than cuboid or cylinder '
                                      'in NexusBuilder.add_detectors_from_idf')

    def __add_detector_transformations(self, detector, detector_group):
        location = detector['location']
        orientation = detector['orientation']
        if location is None and orientation is None:
            return
        translate_unit_vector, translate_magnitude = nexusutils.normalise(location)
        if orientation is not None:
            orientation_transformation = self.add_transformation(detector_group, 'rotation',
                                                                 orientation['angle'],
                                                                 'degrees', orientation['axis'],
                                                                 name='orientation')
            location_transformation = self.add_transformation(detector_group, 'translation',
                                                              translate_magnitude,
                                                              self.length_units, translate_unit_vector,
                                                              depends_on=orientation_transformation,
                                                              name='location')
        else:
            location_transformation = self.add_transformation(detector_group, 'translation',
                                                              translate_magnitude,
                                                              self.length_units, translate_unit_vector,
                                                              name='location')
        self.add_depends_on(detector_group, location_transformation)

    def add_monitors_from_idf(self):
        """
        Add monitors from a Mantid IDF file

        :return: Number of monitors added
        """
        if self.instrument is None:
            raise Exception('There needs to be an NXinstrument before you can add monitors')

        monitors, monitor_types = self.idf_parser.get_monitors()
        monitor_names = [monitor['name'] for monitor in monitors]
        repeated_names = set([name for name in monitor_names if monitor_names.count(name) > 1])
        for monitor in monitors:
            name = monitor['name']
            # If multiple monitors have the same name then append the id to the name
            if name in repeated_names:
                name = name + '_' + str(monitor['id'])
            self.add_monitor(name, monitor['id'], monitor['location'])

        return len(monitors)

    def add_detector(self, name, number, detector_ids, offsets, distance=None, x_pixel_size=None, y_pixel_size=None,
                     diameter=None, thickness=None,
                     x_beam_centre=None, y_beam_centre=None):
        """
        Add an NXdetector, only suitable for rectangular detectors of consistent pixels
        
        :param name: Name of the detector panel
        :param number : Banks are numbered from 1
        :param offsets : Dictionary of pixel offsets
        :param x_pixel_size: Pixel width
        :param y_pixel_size: Pixel height
        :param diameter: If detector is cylindrical this is the diameter
        :param thickness: Pixel thickness
        :param distance: Bank distance along z from parent component
        :param detector_ids: Array of detector pixel id numbers
        :param x_beam_centre: Displacement of the centre of the bank from the beam centre along x
        :param y_beam_centre: Displacement of the centre of the bank from the beam centre along y
        :return: NXdetector group
        """
        optional_scalar_in_metres = {'x_pixel_size': x_pixel_size, 'y_pixel_size': y_pixel_size, 'diameter': diameter,
                                     'thickness': thickness, 'x_beam_centre': x_beam_centre,
                                     'y_beam_centre': y_beam_centre, 'distance': distance}
        self.error_if_not_none_or_scalar(optional_scalar_in_metres)
        detector_group = self.add_detector_minimal(name, number)
        self.__add_distance_datasets(detector_group, optional_scalar_in_metres)
        for dataset_name in offsets:
            offset_dataset = offsets[dataset_name]
            if offset_dataset is not None:
                if isinstance(offset_dataset, h5py._hl.dataset.Dataset):
                    detector_group[dataset_name] = offset_dataset
                else:
                    self.add_dataset(detector_group, dataset_name, offset_dataset, {'units': self.length_units})
        self.add_dataset(detector_group, 'detector_number', np.array(detector_ids).astype(np.dtype('int32')))
        return detector_group

    def __add_distance_datasets(self, group, scalar_params):
        for name, data in scalar_params.items():
            if data is not None:
                self.add_dataset(group, name, data, {'units': self.length_units})

    @staticmethod
    def error_if_not_none_or_scalar(parameters):
        for parameter_name in parameters:
            parameter = parameters[parameter_name]
            if parameter is not None and not nexusutils.is_scalar(parameter):
                raise Exception('In NexusBuilder.add_detector_bank ' + parameter_name + ' must be scalar')

    def add_detector_minimal(self, name, number, depends_on=None):
        """
        Add an NXdetector with minimal details
        
        :param name: Name of the detector panel
        :param number: Detectors are typically numbered from 1
        :param depends_on: Dataset object or name (full path) of axis the detector depends on
        :return: NXdetector group
        """
        if self.instrument is None:
            raise Exception('There needs to be an NXinstrument before you can add detectors')
        detector_group = self.add_nx_group(self.instrument, 'detector_' + str(number), 'NXdetector')
        self.add_dataset(detector_group, 'local_name', name)
        if depends_on is not None:
            self.add_depends_on(detector_group, depends_on)
        return detector_group

    def add_shape(self, group, name, vertices, off_faces, detector_faces=None):
        """
        Add an NXoff_geometry to define geometry in OFF-like format

        :param group: Group or group name to add the NXoff_geometry group to
        :param name: Name of the NXoff_geometry group
        :param vertices: 2D numpy array list of [x,y,z] coordinates of vertices
        :param off_faces: OFF-style vertex indices for each face
        :param detector_faces: Optional array or list of face number-detector id pairs
        :return: NXoff_geometry group
        """
        if isinstance(group, str):
            group = self.root[group]

        vertex_indices, faces = self.create_off_face_vertex_map(off_faces)
        shape = self.add_nx_group(group, name, 'NXoff_geometry')
        self.add_dataset(shape, 'vertices', np.array(vertices).astype('float32'), {'units': self.length_units})
        self.add_dataset(shape, 'vertex_indices', np.array(vertex_indices).astype('int32'))
        self.add_dataset(shape, 'faces', np.array(faces).astype('int32'))
        if detector_faces is not None:
            self.add_dataset(shape, 'detector_faces', np.array(detector_faces).astype('int32'))
        return shape

    def add_tube_pixel(self, group, height, radius, axis, centre=None):
        """
        Construct an NXcylindrical_geometry description of a tube, using basic cylinder description

        :param group: Group to add the pixel geometry to
        :param height: Height of the tube
        :param radius: Radius of the tube
        :param axis: Axis of the tube as a unit vector
        :param centre: On-axis centre of the tube in form [x, y, z]
        :return: NXcylindrical_geometry describing a single pixel
        """
        axis_unit, axis_mag = nexusutils.normalise(axis)
        if not np.isclose([axis_mag], [1.]):
            axis = axis_unit
            logger.warning('Axis vector given to NexusBuilder.add_tube_pixel was not a unit vector. '
                           'Conversion to unit vector was carried out automatically.')
        if centre is None:
            centre = np.array([0., 0., 0.])
        vector_a = centre - (axis * (height * 0.5))
        vector_c = centre + (axis * (height * 0.5))
        vector_b = radius * nexusutils.get_an_orthogonal_unit_vector(vector_a - vector_c)
        vertices = np.array([vector_a, vector_b, vector_c]).astype(float)
        shape = self.add_nx_group(group, 'pixel_shape', 'NXcylindrical_geometry')
        self.add_dataset(shape, 'vertices', vertices, {'units': self.length_units})
        self.add_dataset(shape, 'cylinder', np.array([0, 1, 2]).astype('int32'))

    def add_tube_pixel_mesh(self, group, height, radius, axis, centre=None, number_of_vertices=50):
        """
        Construct an NXoff_geometry description of a tube, using the OFF-style description

        :param group: Group to add the pixel geometry to
        :param height: Height of the tube
        :param radius: Radius of the tube
        :param axis: Axis of the tube as a unit vector
        :param centre: On-axis centre of the tube in form [x, y, z]
        :param number_of_vertices: Maximum number of vertices to use to describe pixel
        :return: NXoff_geometry describing a single pixel
        """
        # Construct the geometry as if the tube axis is along x, rotate everything later
        if centre is None:
            centre = [0, 0, 0]
        end_centre = [centre[0] - (height / 2.0), centre[1], centre[2]]
        angles = np.linspace(0, 2 * np.pi, np.floor((number_of_vertices / 2) + 1))
        # The last point is the same as the first so get rid of it
        angles = angles[:-1]
        y = end_centre[1] + radius * np.cos(angles)
        z = end_centre[2] + radius * np.sin(angles)
        num_points_at_each_tube_end = len(y)
        vertices = np.concatenate((
            np.array(list(zip(np.zeros(len(y)) + end_centre[0], y, z))),
            np.array(list(zip(np.ones(len(y)) * height + end_centre[0], y, z)))))

        # Rotate vertices to correct the tube axis
        rotation_matrix = nexusutils.find_rotation_matrix_between_vectors(np.array(axis), np.array([1., 0., 0.]))
        if rotation_matrix is not None:
            vertices = rotation_matrix.dot(vertices.T).T

        #
        # points around left circle tube-end       points around right circle tube-end
        #                                          (these follow the left ones in vertices list)
        #  circular boundary ^                     ^
        #                    |                     |
        #     nth_vertex + 2 .                     . nth_vertex + num_points_at_each_tube_end + 2
        #     nth_vertex + 1 .                     . nth_vertex + num_points_at_each_tube_end + 1
        #     nth_vertex     .                     . nth_vertex + num_points_at_each_tube_end
        #                    |                     |
        #  circular boundary v                     v
        #
        faces = [
            [nth_vertex, nth_vertex + num_points_at_each_tube_end, nth_vertex + num_points_at_each_tube_end + 1,
             nth_vertex + 1] for nth_vertex in range(num_points_at_each_tube_end - 1)]
        # Append the last rectangular face
        faces.append([num_points_at_each_tube_end - 1, (2 * num_points_at_each_tube_end) - 1,
                      num_points_at_each_tube_end, 0])
        # NB this is a tube, not a cylinder; I'm not adding the circular faces on the ends of the tube
        faces = np.array(faces)
        pixel_shape = self.add_shape(group, 'pixel_shape', vertices, faces)
        return pixel_shape

    def __del__(self):
        # Wrap in try to ignore exception which h5py likes to throw with Python 3.5
        try:
            self.source_file.close()
            self.target_file.close()
        except Exception:
            pass

    def __add_nx_entry(self, nx_entry_name):
        entry_group = self.target_file.create_group(nx_entry_name)
        entry_group.attrs.create('NX_class', np.array('NXentry').astype('|S7'))
        return entry_group

    def __copy_group(self, source_group_name, target_group_name):
        """
        Copy a group with its attributes but without members
    
        :param source_group_name: Name of group in source file
        :param target_group_name: Name of group in target file
        """
        self.target_file.copy(self.source_file[source_group_name], target_group_name, shallow=True)
        for sub_group in self.source_file[source_group_name].keys():
            if sub_group in self.target_file[target_group_name]:
                self.target_file[target_group_name].__delitem__(sub_group)

    def __copy_dataset(self, dataset, target_dataset):
        """
        Copy a dataset with specified compression options and the source dataset's attributes
    
        :param dataset: The dataset being copied
        :param target_dataset: Name of the dataset in the target file
        """
        try:
            d_set = self.target_file.create_dataset(target_dataset, dataset[...].shape, dtype=dataset.dtype,
                                                    compression=self.compress_type, compression_opts=self.compress_opts)
            d_set[...] = dataset[...]
        except TypeError:
            logger.error('Type error copying to dataset: ' + target_dataset + ', value is type: ' + str(
                dataset.dtype))
        except IOError as e:
            logger.error('IO error copying to dataset: ' + target_dataset + ', value is type: ' + str(
                dataset.dtype) + ', errorstr: ' + e.strerror)
        except:
            logger.error('Unexpected error in NexusBuilder.__copy_dataset')
            raise
        # Now copy attributes
        source_attributes = dataset.attrs.items()
        target_attributes = self.target_file[target_dataset].attrs
        for key, value in source_attributes:
            if key != 'target':
                logger.debug('attr key: ' + str(key) + ' value: ' + str(value))
                target_attributes.create(key, value)

    def add_shape_from_file(self, filename, group, name):
        """
        Add an NXoff_geometry shape definition from an OFF file

        :param filename: Name of the OFF file from which to get the geometry
        :param group: Group to add the NXoff_geometry to
        :param name: Name of the NXoff_geometry group to be created
        :return: NXoff_geometry group
        """
        with open(filename) as off_file:
            file_start = off_file.readline()
            if file_start != 'OFF\n':
                logger.error('OFF file is expected to start "OFF", actually started: ' + file_start)
                return None
            counts = off_file.readline().split()
            number_of_vertices = int(counts[0])
            # These values are also in the first line, although we don't need them:
            # number_of_faces = int(counts[1])
            # number_of_edges = int(counts[2])

            off_vertices = np.zeros((number_of_vertices, 3), dtype=float)  # preallocate
            for vertex_number in range(number_of_vertices):
                off_vertices[vertex_number, :] = np.array(off_file.readline().split()).astype(float)

            faces_lines = off_file.readlines()
        all_faces = [np.array(face_line.split()).astype(int) for face_line in faces_lines]

        return self.add_shape(group, name, off_vertices, all_faces)

    @staticmethod
    def create_off_face_vertex_map(off_faces):
        """
        Avoid having a ragged edge faces dataset due to differing numbers of vertices in faces by recording
        a flattened faces dataset (vertex_indices) and putting the start index for each face in that
        into the faces dataset.

        :param off_faces: OFF-style faces array, each row is number of vertices followed by vertex indices
        :return: flattened array (vertex_indices) and the start indices in that (faces)
        """
        faces = []
        vertex_indices = []
        current_index = 0
        for face in off_faces:
            faces.append(current_index)
            current_index += face[0]
            for vertex_index in face[1:]:
                vertex_indices.append(vertex_index)
        return vertex_indices, faces

    def add_structured_detectors_from_idf(self):
        """
        Find structured detectors in the IDF and add corresponding NXgrid_shapes in the NeXus file

        :return: Number of grid shapes added
        """
        detector_number = 1
        for detector in self.idf_parser.get_structured_detectors():
            # Put each one in an NXdetector
            detector_group = self.add_detector_minimal(detector['name'], detector_number)

            off_vertices = self.idf_parser.get_structured_detector_vertices(detector['type_name'])

            # There is one fewer pixel than vertex in each dimension because vertices mark the pixel corners
            pixels_in_first_dimension = off_vertices.shape[0] - 1
            pixels_in_second_dimension = off_vertices.shape[1] - 1

            # Reshape vertices into a 1D list
            off_vertices = np.reshape(off_vertices, (off_vertices.shape[0] * off_vertices.shape[1], 3), order='F')

            detector_ids = self.__create_detector_ids_for_structured_detector(pixels_in_first_dimension,
                                                                              pixels_in_second_dimension, detector)
            quadrilaterals, detector_faces, pixel_offsets = self.__create_quadrilaterals_dataset(
                pixels_in_first_dimension,
                pixels_in_second_dimension,
                detector_ids, off_vertices)

            self.add_shape(detector_group, 'detector_shape', off_vertices, quadrilaterals, detector_faces)
            self.add_dataset(detector_group, 'detector_number', detector_ids)
            self.add_dataset(detector_group, 'x_pixel_offset', pixel_offsets[:, :, 0], {'units': self.length_units})
            self.add_dataset(detector_group, 'y_pixel_offset', pixel_offsets[:, :, 1], {'units': self.length_units})
            z_offsets = pixel_offsets[:, :, 2]
            # Only include z offsets if they are not zero everywhere
            if z_offsets.any():
                self.add_dataset(detector_group, 'z_pixel_offset', z_offsets, {'units': self.length_units})

            self.__add_transformations_for_structured_detector(detector, detector_group)

            detector_number += 1
        total_detectors = detector_number - 1
        return total_detectors

    @staticmethod
    def __create_quadrilaterals_dataset(pixels_in_first_dimension, pixels_in_second_dimension, detector_ids, vertices):
        quadrilaterals = []
        detector_faces = []
        pixel_offsets = np.zeros((pixels_in_second_dimension, pixels_in_first_dimension, 3))
        face_number = 0
        for row_index in range(pixels_in_second_dimension):
            for column_index in range(pixels_in_first_dimension):
                first_pixel = column_index + (row_index * (pixels_in_first_dimension + 1))
                pixel_corner_indices = np.array([first_pixel, first_pixel + pixels_in_first_dimension + 1,
                                                 first_pixel + pixels_in_first_dimension + 2,
                                                 first_pixel + 1])
                pixel_corner_positions = vertices[pixel_corner_indices]

                if row_index != pixels_in_second_dimension and column_index != pixels_in_first_dimension:
                    # Insert 4 at start of each face to indicate 4 vertices in the face (OFF format)
                    quadrilaterals.append(np.insert(pixel_corner_indices, 0, 4))
                    detector_faces.append([face_number, detector_ids[row_index, column_index]])
                    pixel_centre = np.mean(pixel_corner_positions, axis=0)
                    pixel_offsets[row_index, column_index] = pixel_centre

                face_number += 1
        return quadrilaterals, detector_faces, pixel_offsets

    def __add_transformations_for_structured_detector(self, detector, detector_group):
        # Add position of detector
        translate_unit_vector, translate_magnitude = nexusutils.normalise(detector['location'])
        # Add orientation of detector
        if detector['orientation'] is not None:
            rotate_unit_vector, rotate_magnitude = nexusutils.normalise(detector['orientation']['axis'])
            rotation = self.add_transformation(detector_group, 'rotation',
                                               detector['orientation']['angle'],
                                               'degrees',
                                               rotate_unit_vector, name='orientation')
            position = self.add_transformation(detector_group, 'translation', translate_magnitude,
                                               self.length_units,
                                               translate_unit_vector, name='panel_position',
                                               depends_on=rotation)
        else:
            position = self.add_transformation(detector_group, 'translation', translate_magnitude,
                                               self.length_units,
                                               translate_unit_vector, name='panel_position')
        self.add_depends_on(detector_group, position)

    @staticmethod
    def __create_detector_ids_for_structured_detector(pixels_in_first_dimension, pixels_in_second_dimension, detector):
        # Create the id list (detector_number dataset)
        detector_ids = np.arange(detector['id_start'],
                                 pixels_in_second_dimension + detector['id_start'],
                                 detector['X_id_step'])
        detector_ids = np.expand_dims(detector_ids, axis=1)
        for column_number in range(1, pixels_in_first_dimension):
            row_increment = column_number * pixels_in_second_dimension
            new_column = np.arange(detector['id_start'] + row_increment,
                                   detector['id_start'] + row_increment + pixels_in_second_dimension,
                                   detector['X_id_step'])
            new_column = np.expand_dims(new_column, axis=1)
            detector_ids = np.hstack([detector_ids, new_column])
        return detector_ids

    def add_monitor(self, name, detector_id, location, units=None):
        """
        Add a monitor to instrument

        :param name: Name for the monitor group
        :param detector_id: The detector id of the monitor
        :param location: Location of the monitor relative to the source
        :param units: Units of the distances
        :return: NXmonitor
        """
        if self.instrument is None:
            raise Exception('There needs to be an NXinstrument before you can add monitors')
        if units is None:
            units = self.length_units
        monitor_group = self.add_nx_group(self.instrument, name, 'NXmonitor')
        # detector_id is not a monitor dataset in the standard...
        self.add_dataset(monitor_group, 'detector_id', int(detector_id))
        transform_group = self.add_transformation_group(monitor_group)
        location_unit_vector, location_magnitude = nexusutils.normalise(location.astype(float))
        location = self.add_transformation(transform_group, 'translation', location_magnitude, units,
                                           location_unit_vector, name='location')
        self.add_depends_on(monitor_group, location)
        # TODO add monitor shape definition from monitor['shape']
        return monitor_group

    def add_depends_on(self, group, dependee):
        """
        Add a "depends_on" dataset to a group

        :param group: Group to add dataset to
        :param dependee: The dependee as a dataset object or name (full path) string
        :return: The "depends_on" dataset
        """
        if isinstance(dependee, h5py._hl.dataset.Dataset):
            dependee = str(dependee.name)
        return self.add_dataset(group, 'depends_on', dependee)

    def add_transformation_group(self, group):
        """
        Add an NXtransformation group
        :param group: Add NXtransformation to this group
        :return: NXtransformation group
        """
        if isinstance(group, str):
            group = self.root[group]
        return self.add_nx_group(group, 'transformations', 'NXtransformation')

    def add_instrument(self, name, instrument_group_name='instrument'):
        """
        Add an NXinstrument with specified name

        :param name: Name of the instrument
        :param instrument_group_name: Name for the NXinstrument group
        :return: NXinstrument
        """
        self.instrument = self.add_nx_group(self.root, instrument_group_name, 'NXinstrument')
        if len(name) > 2:
            self.add_dataset(self.instrument, 'name', name, {'short_name': name[:3]})
        else:
            self.add_dataset(self.instrument, 'name', name, {'short_name': name})

    def add_transformation(self, group, transformation_type, values, units, vector, offset=None, name='transformation',
                           depends_on='.'):
        """
        Add an NXtransformation

        :param group: The group to add the translation to, for example an instrument component
        :param transformation_type: "translation" or "rotation"
        :param values: Values to add to the dataset: distance to translate or angle to rotate
        :param units: Units for the dataset's values
        :param vector: Unit vector to translate along or rotate around
        :param offset: Offset translation to apply to the axis before applying transformation
        :param name: Name of this transformation axis, for example "rotation_angle", "phi", "panel_translate", etc
        :param depends_on: Name (full path) of another NXtransformation which must be carried out before this one
        :return: The NXtransformation
        """
        transform_types = ['translation', 'rotation']
        if transformation_type not in transform_types:
            raise Exception('Transformation must be one of these types (' + ' '.join(transform_types) + ')')
        if isinstance(depends_on, h5py._hl.dataset.Dataset):
            depends_on = str(depends_on.name)
        attributes = {'units': units,
                      'vector': vector,
                      'transformation_type': transformation_type,
                      'depends_on': depends_on,  # terminate chain with "." if no depends_on given
                      'NXclass': 'NXtransformation'}
        if offset is not None:
            attributes['offset'] = offset
        return self.add_dataset(group, name, values, attributes)

    def add_instrument_geometry_from_idf(self):
        """
        Get all the geometry information we can from the IDF file
        """
        instrument_name = self.idf_parser.get_instrument_name()
        self.add_instrument(instrument_name)
        logger.info('Got instrument geometry for ' + instrument_name + ' from IDF file, it has:')

        source_name = self.idf_parser.get_source_name()
        self.add_source(source_name)
        logger.info('a source called ' + source_name)

        sample_position_list = self.idf_parser.get_sample_position()
        sample_group = self.add_sample(sample_position_list)
        logger.info('a sample at x=' + str(sample_position_list[0]) + ', y=' + str(sample_position_list[1]) + ', z=' +
                    str(sample_position_list[2]) + ' offset from source')

        number_of_monitors = self.add_monitors_from_idf()
        if number_of_monitors != 0:
            logger.info(str(number_of_monitors) + ' monitors')

        number_of_grid_detectors = self.add_structured_detectors_from_idf()
        number_of_detectors = 0
        if number_of_grid_detectors != 0:
            logger.info(str(number_of_grid_detectors) + ' topologically, grid detector panels')
        else:
            number_of_detectors = self.add_detectors_from_idf()
            if number_of_detectors != 0:
                logger.info(str(number_of_detectors) + ' detector panels')

        detectors_added = (number_of_detectors + number_of_grid_detectors) > 0
        return detectors_added

    def add_sample(self, position, name='sample'):
        """
        Add an NXsample group

        :param position: Distance along the beam from the source
        :param name: Name for the NXsample group
        :return: The NXsample group and the sample position dataset
        """
        sample_group = self.add_nx_group(self.root, name, 'NXsample')
        if position is None:
            position = np.array([0.0, 0.0, 0.0])

        sample_transform_group = self.add_transformation_group('sample')
        self.add_dataset('sample', 'distance', position[2])
        position_unit_vector, position_magnitude = nexusutils.normalise(np.array(position).astype(float))
        sample_position = self.add_transformation(sample_transform_group, 'translation', position_magnitude,
                                                  self.length_units,
                                                  position_unit_vector, name='location')
        self.add_depends_on(sample_group, sample_position)
        return sample_group

    def add_source(self, name, group_name='source'):
        """
        Add an NXsource group

        :param name: Name of the source
        :param group_name: Name for the NXsource group
        :return: The NXsource group
        """
        if self.instrument is None:
            raise Exception('There needs to be an NXinstrument before you can add an NXsource')
        source_group = self.add_nx_group(self.instrument, group_name, 'NXsource')
        self.add_dataset(source_group, 'name', name)
        return source_group

    @staticmethod
    def add_nx_group(parent_group, group_name, nx_class_name):
        """
        Add an NXclass group

        :param parent_group: The parent group object
        :param group_name: Name for the group, any spaces are replaced with underscores
        :param nx_class_name: Name of the NXclass
        :return:
        """
        group_name = group_name.replace(' ', '_')
        created_group = parent_group.create_group(group_name)
        created_group.attrs.create('NX_class', np.array(nx_class_name).astype('|S' + str(len(nx_class_name))))
        return created_group
