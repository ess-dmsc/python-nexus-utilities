import numpy as np
import h5py
import logging
from readwriteoff import write_off_file, create_off_face_vertex_map, construct_cylinder_mesh
from detectorplotter import get_transformations, do_transformations
import nexusutils

logger = logging.getLogger('NeXus_Utils')


def find_geometry_groups(nexus_file):
    hits = []

    def _visit_groups(name, obj):
        if "NX_class" in obj.attrs.keys():
            if str(obj.attrs["NX_class"], 'utf8') in ["NXoff_geometry", "NXcylindrical_geometry"]:
                hits.append(obj)

    nexus_file.visititems(_visit_groups)
    return hits


def get_off_geometry_from_group(group, nexus_file):
    vertices = group['vertices'][...]
    vertices = get_and_apply_transformations(group, nexus_file, vertices)
    return vertices, group['faces'][...], group['winding_order'][...]


def get_and_apply_transformations(geometry_group, nexus_file, vertices):
    transformations = list()
    try:
        depends_on = geometry_group.parent.get('depends_on')
    except:
        depends_on = '.'
    get_transformations(depends_on, transformations, nexus_file)

    vertices = np.matrix(vertices.T)
    # Add fourth element of 1 to each vertex, indicating these are positions not direction vectors
    vertices = np.matrix(np.vstack((vertices, np.ones(vertices.shape[1]))))
    vertices = do_transformations(transformations, vertices)
    # Now the transformations are done we do not need the 4th element
    return vertices[:3, :].T


def get_cylindrical_geometry_from_group(group, nexus_file):
    cylinders = group['cylinder'][...]
    group_vertices = group['vertices'][...]
    vertices = None
    faces = None
    winding_order = None
    for cylinder in cylinders:
        vector_a = group_vertices[cylinder[0], :]
        vector_b = group_vertices[cylinder[1], :]
        vector_c = group_vertices[cylinder[2], :]

        axis = vector_a-vector_c
        unit_axis, height = nexusutils.normalise(axis)
        radius = nexusutils.calculate_magnitude(vector_b - vector_a)
        centre = (vector_a + vector_c) * 0.5

        mesh_vertices, mesh_faces = construct_cylinder_mesh(height, radius, unit_axis, centre)
        new_winding_order, new_faces = create_off_face_vertex_map(mesh_faces)
        vertices, faces, winding_order = accumulate_geometry(vertices, faces, winding_order, mesh_vertices, new_faces,
                                                             new_winding_order)
    get_and_apply_transformations(group, nexus_file, vertices)
    return vertices, faces, winding_order


def get_geometry_from_group(group, nexus_file):
    #if group.name.split('/')[-1] == "pixel_shape":
    #    raise NotImplementedError("Parsing pixel_shape groups not yet implemented.")
    if str(group.attrs["NX_class"], 'utf8') == "NXoff_geometry":
        return get_off_geometry_from_group(group, nexus_file)
    elif str(group.attrs["NX_class"], 'utf8') == "NXcylindrical_geometry":
        return get_cylindrical_geometry_from_group(group, nexus_file)


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
        group_vertices, group_faces, group_winding_order = get_geometry_from_group(group, nexus_file)
        group_vertices *= 100.  # scale it! TODO temp!
        vertices, faces, winding_order = accumulate_geometry(vertices, faces, winding_order, group_vertices,
                                                             group_faces, group_winding_order)
    write_off_file(off_filename, vertices, faces, winding_order)


def accumulate_geometry(vertices, faces, winding_order, new_vertices, new_faces, new_winding_order):
    if faces is not None:
        faces = np.concatenate((faces, new_faces + winding_order.size))
    else:
        faces = new_faces

    if winding_order is not None:
        winding_order = np.concatenate((winding_order, new_winding_order + vertices.shape[0]))
    else:
        winding_order = new_winding_order

    if vertices is not None:
        vertices = np.vstack((vertices, new_vertices))
    else:
        vertices = new_vertices
    return vertices, faces, winding_order


if __name__ == '__main__':
    from drawoff import render_off_from_file
    # nexus_geometry_to_off_file("example_instruments/off_files/example_nx_geometry.nxs", "output_OFF_file.off")
    # nexus_geometry_to_off_file("example_instruments/loki/LOKI_example_gzip.hdf5", "output_OFF_file.off")
    # nexus_geometry_to_off_file("example_instruments/wish/WISH_example_gzip_compress.hdf5", "output_OFF_file.off")
    nexus_geometry_to_off_file("example_instruments/sans2d/SANS_example_gzip_compress.hdf5", "output_OFF_file.off")
    render_off_from_file('output_OFF_file.off')
