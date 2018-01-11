import numpy as np
import h5py
import logging
from readwriteoff import write_off_file

logger = logging.getLogger('NeXus_Utils')


def find_geometry_groups(nexus_file):
    hits = []

    def _visit_groups(name, obj):
        if "NX_class" in obj.attrs.keys():
            if "NXoff_geometry" == str(obj.attrs["NX_class"], 'utf8'):
                hits.append(obj)

    nexus_file.visititems(_visit_groups)
    return hits


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
        if faces:
            faces = group['faces'][...] + winding_order.size
        else:
            faces = group['faces'][...]

        if winding_order:
            # TODO shape[1] or shape[0]? (the answer not equal to 3)
            winding_order = group['winding_order'][...] + vertices.shape[1]
        else:
            winding_order = group['winding_order'][...]

        if vertices:
            vertices = np.vstack((vertices, group['vertices'][...]))
        else:
            vertices = group['vertices'][...]
    write_off_file(off_filename, vertices, faces, winding_order)


if __name__ == '__main__':
    nexus_geometry_to_off_file("example_instruments/teapot/example_nx_geometry.nxs", "output_OFF_file.off")
