import h5py
import numpy as np
import matplotlib.pyplot as plt
import nexusutils


class DetectorPlotter:
    """
    Produce a simple scatter plot of detector pixel locations
    """

    def __init__(self, nexus_filename):
        self.source_file = h5py.File(nexus_filename, 'r')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.source_file is not None:
            self.source_file.close()

    def plot_pixel_positions(self):
        instrument_group = self.source_file['/raw_data_1/instrument']
        detector_group_paths = []
        for name, dataset_or_group in instrument_group.items():
            if 'NX_class' in dataset_or_group.attrs:
                if dataset_or_group.attrs['NX_class'].astype(str) == 'NXdetector':
                    detector_group_paths.append(dataset_or_group.name)
        fig, ax = plt.subplots(nrows=2, ncols=1)
        for detector_path in detector_group_paths:
            detector_group = self.source_file.get(detector_path)
            x_offsets = detector_group.get('x_pixel_offset')
            y_offsets = detector_group.get('y_pixel_offset')
            z_offsets = detector_group.get('z_pixel_offset')
            if z_offsets is None:
                z_offsets = np.zeros_like(x_offsets)
            x_offsets = x_offsets[:]
            y_offsets = y_offsets[:]
            z_offsets = z_offsets[:]

            depends_on = detector_group.get('depends_on')
            transformations = list()
            get_transformations(depends_on, transformations, self.source_file)
            vertices = do_transformations(transformations,
                                          reshape_offsets(x_offsets, y_offsets, z_offsets))

            x_offsets = vertices[0, :].A1
            y_offsets = vertices[1, :].A1
            z_offsets = vertices[2, :].A1

            ax[0].scatter(x_offsets, y_offsets, s=0.75, marker='x')
            ax[1].scatter(x_offsets, z_offsets, s=0.75, marker='x')

        ax[0].set_title('XY-plane pixel locations')
        ax[1].set_title('XZ-plane pixel locations')
        plt.axis('equal')
        plt.show()


def get_transformations(depends_on, transformations, source_file):
    """
    Get all transformations in the depends_on chain
    NB, these need to then be applied in reverse order

    :param depends_on: The first depends_on path string
    :param transformations: List of transformations to populate
    :param source_file: The NeXus file object
    """
    if depends_on is not None:
        try:
            transform_path = str(depends_on[...].astype(str))
        except:
            transform_path = depends_on.decode()
        if transform_path != '.':
            transform = source_file.get(transform_path)
            next_depends_on = get_transformation(transform, transformations)
            get_transformations(next_depends_on, transformations, source_file)


def get_transformation(transform, transformations):
    attributes = transform.attrs
    offset = [0., 0., 0.]
    if 'offset' in attributes:
        offset = attributes['offset'].astype(float)
    if attributes['transformation_type'].astype(str) == 'translation':
        vector = attributes['vector'] * transform[...].astype(float)
        matrix = np.matrix([[1., 0., 0., vector[0] + offset[0]],
                            [0., 1., 0., vector[1] + offset[1]],
                            [0., 0., 1., vector[2] + offset[2]],
                            [0., 0., 0., 1.]])
        transformations.append(matrix)

    elif attributes['transformation_type'].astype(str) == 'rotation':
        axis = attributes['vector']
        angle = np.deg2rad(transform[...])
        rotation_matrix = nexusutils.rotation_matrix_from_axis_and_angle(axis, angle)
        matrix = np.matrix([[rotation_matrix[0, 0], rotation_matrix[0, 1], rotation_matrix[0, 2], offset[0]],
                            [rotation_matrix[1, 0], rotation_matrix[1, 1], rotation_matrix[1, 2], offset[1]],
                            [rotation_matrix[2, 0], rotation_matrix[2, 1], rotation_matrix[2, 2], offset[2]],
                            [0., 0., 0., 1.]])
        transformations.append(matrix)
    return attributes['depends_on']


def reshape_offsets(x_offsets, y_offsets, z_offsets):
    if len(x_offsets.shape) > 1:
        x_offsets = np.reshape(x_offsets, (1, np.prod(x_offsets.shape)))
        y_offsets = np.reshape(y_offsets, (1, np.prod(x_offsets.shape)))
        z_offsets = np.reshape(z_offsets, (1, np.prod(x_offsets.shape)))
    offsets = np.matrix(np.vstack((x_offsets, y_offsets, z_offsets, np.ones(x_offsets.shape))))
    return offsets


def do_transformations(transformations, vertices):
    for transformation in transformations:
        for column_index in range(vertices.shape[1]):
            vertices[:, column_index] = transformation * np.matrix(vertices[:, column_index])
    return vertices
