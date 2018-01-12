import numpy as np
import h5py
import logging
from readwriteoff import write_off_file
from detectorplotter import get_transformations, do_transformations

logger = logging.getLogger('NeXus_Utils')


def find_geometry_groups(nexus_file):
    hits = []

    def _visit_groups(name, obj):
        if "NX_class" in obj.attrs.keys():
            if "NXoff_geometry" == str(obj.attrs["NX_class"], 'utf8'):
                hits.append(obj)

    nexus_file.visititems(_visit_groups)
    return hits


def get_vertices(group, nexus_file):
    vertices = group['vertices'][...]
    transformations = list()
    try:
        depends_on = group.parent.get('depends_on')
    except:
        depends_on = '.'
    get_transformations(depends_on, transformations, nexus_file)

    vertices = np.matrix(vertices.T)
    # Add fourth element of 1 to each vertex, indicating these are positions not direction vectors
    vertices = np.matrix(np.vstack((vertices, np.ones(vertices.shape[1]))))
    vertices = do_transformations(transformations, vertices)
    # Now the transformations are done we do not need the 4th element
    return vertices[:3, :].T


def nexus_geometry_to_off_file(nexus_filename, off_filename):
    """

    :param nexus_filename:
    :param off_filename:
    :return:
    """
    nexus_file = h5py.File(nexus_filename, 'r')
    geometry_groups = find_geometry_groups(nexus_file)
    # Build up vertices, faces and winding order
    vertices = None
    faces = None
    winding_order = None
    for group in geometry_groups:
        group_vertices = get_vertices(group, nexus_file)
        if faces is not None:
            faces = np.concatenate((faces, group['faces'][...] + winding_order.size))
        else:
            faces = group['faces'][...]

        if winding_order is not None:
            winding_order = np.concatenate((winding_order, group['winding_order'][...] + vertices.shape[0]))
        else:
            winding_order = group['winding_order'][...]

        if vertices is not None:
            vertices = np.vstack((vertices, group_vertices))
        else:
            vertices = group_vertices
    write_off_file(off_filename, vertices, faces, winding_order)


if __name__ == '__main__':
    from drawoff import render_off_from_file
    #nexus_geometry_to_off_file("example_instruments/off_files/example_nx_geometry.nxs", "output_OFF_file.off")
    nexus_geometry_to_off_file("example_instruments/loki/LOKI_example_gzip.hdf5", "output_OFF_file.off")
    render_off_from_file('output_OFF_file.off')
