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
                 nx_entry_name='raw_data_1', idf_filename=None):
        """
        compress_type=32001 for BLOSC

        :param output_nexus_filename: Name of the output file
        :param input_nexus_filename: Name of the input file
        :param nx_entry_name: Name of the root group (NXentry class)
        :param compress_type: Name or id of compression filter https://support.hdfgroup.org/services/contributions.html
        :param compress_opts: Compression options, for example gzip compression level
        :param idf_filename: Filename of a Mantid IDF file from which to get instrument geometry
        """
        self.compress_type = compress_type
        self.compress_opts = compress_opts
        nexusutils.wipe_file(output_nexus_filename)
        if input_nexus_filename:
            self.source_file = h5py.File(input_nexus_filename, 'r')
        else:
            self.source_file = None
        self.target_file = h5py.File(output_nexus_filename, 'r+')
        # Having an NXentry root group is compulsory in NeXus format
        self.root = self.__add_nx_entry(nx_entry_name)
        if idf_filename:
            self.idf_parser = IDFParser(idf_filename)
            self.length_units = self.idf_parser.get_length_units()
        else:
            self.idf_parser = None
            self.length_units = 'm'
        self.instrument = None

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
        user_group = nexusutils.add_nx_group(self.root, 'user_' + str(number), 'NXuser')
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
            data = [data]
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
        NB, currently only works for "RectangularDetector" panels 
            currently assumes the coordinate system in the IDF is the same as the NeXus one
            (z is beam direction, x is the other horizontal, y is vertical)

        :return: Number of detector panels added
        """
        if self.idf_parser is None:
            logger.error('No IDF file was given to the NexusBuilder, cannot call add_detector_banks_from_idf')
        total_panels = 0
        detectors = self.idf_parser.get_detectors()
        # for det_info, pixel_shape in self.idf_parser.get_detectors():
        #     total_panels += 1
        #     det_bank_group = self.add_detector(det_info['name'], det_info['number'], det_info['detector_ids'],
        #                                        det_info['x_pixel_offset'], det_info['y_pixel_offset'],
        #                                        det_info['distance'][2], pixel_shape['x_pixel_size'],
        #                                        pixel_shape['y_pixel_size'], pixel_shape['diameter'],
        #                                        thickness=pixel_shape['thickness'],
        #                                        x_beam_centre=det_info['distance'][0],
        #                                        y_beam_centre=det_info['distance'][1])
        #     if 'transformation' in det_info:
        #         pass
        #         # self.add_transformation(det_bank_group, det_info['transformation'])
        return total_panels

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

    def add_detector(self, name, number, detector_ids, x_pixel_offset,
                     y_pixel_offset, distance=None, x_pixel_size=None, y_pixel_size=None, diameter=None, thickness=None,
                     x_beam_centre=None, y_beam_centre=None):
        """
        Add an NXdetector, only suitable for rectangular detectors of consistent pixels
        
        :param name: Name of the detector panel
        :param number : Banks are numbered from 1
        :param x_pixel_size: Pixel width
        :param y_pixel_size: Pixel height
        :param diameter: If detector is cylindrical this is the diameter
        :param thickness: Pixel thickness
        :param distance: Bank distance along z from parent component
        :param detector_ids: Array of detector pixel id numbers
        :param x_beam_centre: Displacement of the centre of the bank from the beam centre along x
        :param y_beam_centre: Displacement of the centre of the bank from the beam centre along y
        :param x_pixel_offset: Pixel offsets on x axis from centre of detector
        :param y_pixel_offset: Pixel offsets on y axis from centre of detector
        :return: NXdetector group
        """
        optional_scalar_in_metres = {'x_pixel_size': x_pixel_size, 'y_pixel_size': y_pixel_size, 'diameter': diameter,
                                     'thickness': thickness, 'x_beam_centre': x_beam_centre,
                                     'y_beam_centre': y_beam_centre, 'distance': distance}
        self.error_if_not_none_or_scalar(optional_scalar_in_metres)
        detector_group = self.add_detector_minimal(name, number)
        self.__add_distance_datasets(detector_group, optional_scalar_in_metres)
        self.add_dataset(detector_group, 'x_pixel_offset', x_pixel_offset, {'units': self.length_units})
        self.add_dataset(detector_group, 'y_pixel_offset', y_pixel_offset, {'units': self.length_units})
        self.add_dataset(detector_group, 'detector_number', detector_ids)
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
        detector_group = nexusutils.add_nx_group(self.instrument, 'detector_' + str(number), 'NXdetector')
        self.add_dataset(detector_group, 'local_name', name)
        if depends_on is not None:
            self.add_depends_on(detector_group, depends_on)
        return detector_group

    def add_shape(self, group, name, vertices, faces, detector_faces=None):
        """
        Add an NXshape to define geometry in OFF-like format

        :param group: Group or group name to add the NXshape group to
        :param name: Name of the NXshape group
        :param vertices: 2D numpy array list of [x,y,z] coordinates of vertices
        :param faces: 2D numpy array list of vertex indices in each face, right-hand rule for face normal
                      or a list of these where with an arrays for faces with different number of vertices
        :param detector_faces: Optional 2D numpy array list of face number-detector id pairs
        :return: NXshape group
        """
        if isinstance(group, str):
            group = self.root[group]

        shape = nexusutils.add_nx_group(group, name, 'NXshape')
        self.add_dataset(shape, 'vertices', vertices)
        if isinstance(faces, list):
            for face_types in faces:
                self.add_dataset(shape, 'faces_' + str(face_types.shape[1]), face_types,
                                 {'vertices_per_face': face_types.shape[1]})
        else:
            self.add_dataset(shape, 'faces', faces, {'vertices_per_face': faces.shape[1]})
        if detector_faces is not None:
            self.add_dataset(shape, 'detector_vertices', detector_faces)
        return shape

    def add_tube_pixel(self, group, height, radius, centre=None, number_of_vertices=100):
        """
        Axis is assumed to be along x
        :param group: Group to add the pixel geometry to
        :param height: Height of the tube
        :param radius: Radius of the tube
        :param centre: On-axis centre at the end of the tube in form [x, y, z]
        :param number_of_vertices: Maximum number of vertices to use to describe pixel
        :return: NXshape describing a single pixel
        """
        if centre is None:
            centre = [0, 0, 0]
        angles = np.linspace(0, 2 * np.pi, np.floor((number_of_vertices / 2) + 1))
        # The last point is the same as the first so get rid of it
        angles = angles[:-1]
        y = centre[1] + radius * np.cos(angles)
        z = centre[2] + radius * np.sin(angles)
        num_points_at_each_tube_end = len(y)
        vertices = np.concatenate((
            np.array(list(zip(np.zeros(len(y)), y, z))),
            np.array(list(zip(np.ones(len(y)) * height, y, z)))))
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

    def add_grid_pattern(self, detector_group, name, id_start, position_start, size, id_steps, steps, depends_on='.'):
        """
        Add an NXgrid_pattern
        NB, will need to add a pixel_shape definition to it afterwards

        :param detector_group: NXdetector group to add grid pattern to
        :param name: Name of the NXgrid_pattern group
        :param id_start: The lowest detector id in the grid
        :param position_start: Vector defining the position of the detector pixel with the lowest id
        :param size: Iterable containing the number of pixels in each dimension of the grid
        :param id_steps: Iterable of scalars defining increase in id number along each grid dimension
        :param steps: Iterable of vectors defining translation along each grid dimension to get to next pixel
        :param depends_on: Name (full path) of axis that this component depends on
        :return: NXgrid_pattern group
        """
        grid_pattern = nexusutils.add_nx_group(detector_group, name, 'NXgrid_pattern')
        self.add_dataset(grid_pattern, 'id_start', np.array([id_start]))
        self.add_dataset(grid_pattern, 'position_start', position_start, {'units': self.length_units})
        self.add_dataset(grid_pattern, 'size', np.array([size]))
        self.add_dataset(grid_pattern, 'X_id_step', np.array([id_steps[0]]))
        self.add_dataset(grid_pattern, 'Y_id_step', np.array([id_steps[1]]))
        if len(id_steps) > 2:
            self.add_dataset(grid_pattern, 'Z_id_step', np.array([id_steps[2]]))
        self.add_dataset(grid_pattern, 'X_step', [steps[0]], {'units': self.length_units})
        self.add_dataset(grid_pattern, 'Y_step', [steps[1]], {'units': self.length_units})
        if len(steps) > 2:
            self.add_dataset(grid_pattern, 'Z_step', [steps[2]], {'units': self.length_units})
        self.add_depends_on(grid_pattern, depends_on)
        return grid_pattern

    def __add_pixel_direction(self, detector_module, name, pixel_direction_offset, pixel_direction_step,
                              direction_size):
        if all(arg is not None for arg in [name, pixel_direction_offset, pixel_direction_step, direction_size]):
            if len(pixel_direction_offset) != 3:
                logger.error(
                    'In add_detector_module the pixel direction offset' +
                    ' must each have three values (corresponding to the cartesian axes)' +
                    ' Module name: ' + name)
            self.add_dataset(detector_module, name, 0, {'transformation_type': 'translation',
                                                        'offset_units': self.length_units,
                                                        'offset': pixel_direction_offset,
                                                        'size_in_pixels': direction_size,
                                                        'pixel_number_step': pixel_direction_step})
        else:
            logger.debug('Missing arguments in __add_pixel_direction to define direction: ' + name)

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
        Add an NXshape shape definition from an OFF file

        :param filename: Name of the OFF file from which to get the geometry
        :param group: Group to add the NXshape to
        :param name: Name of the NXshape group to be created
        :return: NXshape group
        """
        with open(filename) as off_file:
            file_start = off_file.readline()
            if file_start != 'OFF\n':
                logger.error('OFF file is expected to start "OFF", actually started: ' + file_start)
                return None
            counts = off_file.readline().split()
            number_of_vertices = int(counts[0])
            # number_of_faces = int(counts[1])
            # number_of_edges = int(counts[2])

            vertices = np.zeros((number_of_vertices, 3), dtype=float)  # preallocate
            for vertex_number in range(number_of_vertices):
                vertices[vertex_number, :] = np.array(off_file.readline().split()).astype(float)

            faces_lines = off_file.readlines()
        all_faces = [np.array(face_line.split()).astype(int) for face_line in faces_lines]
        # Set of each possible number of vertices in a face
        vertices_in_faces = {each_face[0] for each_face in all_faces}
        faces = []
        for vertices_in_face in vertices_in_faces:
            faces.append(np.array([face[1:] for face in all_faces if face[0] == vertices_in_face], dtype='int32'))

        return self.add_shape(group, name, vertices, faces)

    def add_grid_shapes_from_idf(self):
        """
        Find structured detectors in the IDF and add corresponding NXgrid_shapes in the NeXus file

        :return: Number of grid shapes added
        """
        detector_number = 0
        for detector in self.idf_parser.get_structured_detectors():
            # Put each one in an NXdetector
            detector_group = self.add_detector_minimal(detector['name'], detector_number)
            # Add the grid shape
            self.add_grid_shape_from_idf(detector_group, 'grid_shape', detector['type_name'],
                                         detector['id_start'], detector['X_id_step'],
                                         detector['Y_id_step'])
            # Add translation of detector
            translate_vector = np.array(
                [detector['location']['x'], detector['location']['y'], detector['location']['z']]).astype(float)
            translate_unit_vector, translate_magnitude = nexusutils.normalise(translate_vector)
            transform_group = self.add_transformation_group(detector_group)
            position = self.add_transformation(transform_group, 'translation', translate_magnitude, self.length_units,
                                               translate_unit_vector, name='panel_position')

            # Add rotation of detector
            if detector['rotation'] is not None:
                rotate_vector = np.array(
                    [detector['rotation']['axis_x'], detector['rotation']['axis_y'],
                     detector['rotation']['axis_z']]).astype(float)
                rotate_unit_vector, rotate_magnitude = nexusutils.normalise(rotate_vector)
                rotation = self.add_transformation(transform_group, 'rotation', float(detector['rotation']['angle']),
                                                   'degrees',
                                                   rotate_unit_vector, name='panel_orientation',
                                                   depends_on=str(position.name))
                self.add_depends_on(detector_group, rotation)
            else:
                self.add_depends_on(detector_group, position)

            detector_number += 1
        return detector_number

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
        monitor_group = nexusutils.add_nx_group(self.instrument, name, 'NXmonitor')
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
        return nexusutils.add_nx_group(group, 'transformations', 'NXtransformation')

    def add_grid_shape_from_idf(self, group, name, type_name, id_start, X_id_step, Y_id_step, Z_id_step=None):
        """
        Add NXgrid_shape from a StructuredDetector in a Mantid IDF file

        :param group: Group object or name in which to add the NXgrid_shape
        :param name: Name of the NXgrid_shape to be created
        :param type_name: Name of the type in the IDF containing the vertex list for the grid
        :param id_start: Lowest pixel id in the grid
        :param X_id_step: Each pixel along the first dimension of the grid the pixel id increases by this number
        :param Y_id_step: Each pixel along the second dimension of the grid the pixel id increases by this number
        :param Z_id_step: Each pixel along the third dimension of the grid the pixel id increases by this number
        :return: NXgrid_shape group
        """
        if self.idf_parser is None:
            logger.error('No IDF file was given to the NexusBuilder, cannot call add_grid_shape_from_idf')
        if isinstance(group, str):
            group = self.root[group]
        vertices = self.idf_parser.get_structured_detector_vertices(type_name)
        grid_shape = nexusutils.add_nx_group(group, name, 'NXgrid_shape')
        self.add_dataset(grid_shape, 'vertices', vertices, {'units': 'metres'})
        self.add_dataset(grid_shape, 'id_start', id_start)
        self.add_dataset(grid_shape, 'X_id_step', X_id_step)
        self.add_dataset(grid_shape, 'Y_id_step', Y_id_step)
        if Z_id_step:
            self.add_dataset(grid_shape, 'Z_id_step', Z_id_step)
        return grid_shape

    def add_instrument(self, name, instrument_group_name='instrument'):
        """
        Add an NXinstrument with specified name

        :param name: Name of the instrument
        :param instrument_group_name: Name for the NXinstrument group
        :return: NXinstrument
        """
        self.instrument = nexusutils.add_nx_group(self.root, instrument_group_name, 'NXinstrument')
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
        logger.info('Got instrument geometry for ' + instrument_name + ' from IDF file ' + self.idf_parser.filename
                    + ', it has:')

        source_name = self.idf_parser.get_source_name()
        self.add_source(source_name)
        logger.info('a source called ' + source_name)

        sample_position_list = self.idf_parser.get_sample_position()
        sample_group, sample_position = self.add_sample(sample_position_list)
        logger.info('a sample at x=' + str(sample_position_list[0]) + ', y=' + str(sample_position_list[1]) + ', z=' +
                    str(sample_position_list[2]) + ' offset from source')

        number_of_monitors = self.add_monitors_from_idf()
        if number_of_monitors != 0:
            logger.info(str(number_of_monitors) + ' monitors')

        number_of_detectors = self.add_grid_shapes_from_idf()
        if number_of_detectors != 0:
            logger.info(str(number_of_detectors) + ' topologically, grid detector panels')

        return sample_position

    def add_sample(self, position, name='sample'):
        """
        Add an NXsample group

        :param position: Distance along the beam from the source
        :param name: Name for the NXsample group
        :return: The NXsample group and the sample position dataset
        """
        sample_group = nexusutils.add_nx_group(self.root, name, 'NXsample')
        self.add_dataset('sample', 'distance', position[2])
        sample_transform_group = self.add_transformation_group('sample')
        position_unit_vector, position_magnitude = nexusutils.normalise(np.array(position).astype(float))
        sample_position = self.add_transformation(sample_transform_group, 'translation', position_magnitude,
                                                  self.length_units,
                                                  position_unit_vector, name='location')
        self.add_depends_on(sample_group, sample_position)
        return sample_group, sample_position

    def add_source(self, name, group_name='source'):
        """
        Add an NXsource group

        :param name: Name of the source
        :param group_name: Name for the NXsource group
        :return: The NXsource group
        """
        if self.instrument is None:
            raise Exception('There needs to be an NXinstrument before you can add an NXsource')
        source_group = nexusutils.add_nx_group(self.instrument, group_name, 'NXsource')
        self.add_dataset(source_group, 'name', name)
        return source_group
