import numpy as np
import h5py
import logging
from nexusutils.readwriteoff import (
    write_off_file,
    create_off_face_vertex_map,
    construct_cylinder_mesh,
)
from nexusutils.detectorplotter import do_transformations
from nexusutils.utils import normalise, calculate_magnitude

logger = logging.getLogger("NeXus_Utils")


def find_geometry_groups(nexus_file):
    """
    Find all kinds of group containing geometry information.
    Geometry groups themselves are often links (to reuse repeated geometry) so look for parents of geometry groups
    instead and return parent and child dictionary pairs.

    :param nexus_file: NeXus file input
    :return: list of geometry groups and their parent group
    """
    hits = []

    def _visit_groups(name, obj):
        if isinstance(obj, h5py.Group):
            for child_name in obj:
                child = obj[child_name]
                if isinstance(child, h5py.Group):
                    if "NX_class" in child.attrs.keys():
                        if str(child.attrs["NX_class"], "utf8") in [
                            "NXoff_geometry",
                            "NXcylindrical_geometry",
                        ]:
                            hits.append({"parent_group": obj, "geometry_group": child})

    nexus_file.visititems(_visit_groups)
    return hits


def get_off_geometry_from_group(group):
    """
    Get geometry information from an NXoff_geometry group

    :param group:  NXoff_geometry and parent group in dictionary
    :return: vertices, faces and winding_order information from the group
    """
    vertices = group["geometry_group"]["vertices"][...]
    return (
        vertices,
        group["geometry_group"]["faces"][...],
        group["geometry_group"]["winding_order"][...],
    )


def get_and_apply_transformations(group, nexus_file, vertices):
    from nexusutils.detectorplotter import get_transformations

    transformations = list()
    try:
        depends_on = group["parent_group"].get("depends_on")
    except Exception:
        depends_on = "."
    get_transformations(depends_on, transformations, nexus_file)

    vertices = np.matrix(vertices.T)
    # Add fourth element of 1 to each vertex, indicating these are positions not direction vectors
    vertices = np.matrix(np.vstack((vertices, np.ones(vertices.shape[1]))))
    vertices = do_transformations(transformations, vertices)
    # Now the transformations are done we do not need the 4th element
    return vertices[:3, :].T


def get_cylindrical_geometry_from_group(group):
    """
    Get geometry information from an NXcylindrical_geometry group

    :param group:  NXcylindrical_geometry group and its parent group in a dictionary
    :return: vertices, faces and winding_order information from the group
    """
    cylinders = group["geometry_group"]["cylinders"][...]
    group_vertices = group["geometry_group"]["vertices"][...]
    vertices = None
    faces = None
    winding_order = None
    for cylinder in cylinders:
        vector_a = group_vertices[cylinder[0], :]
        vector_b = group_vertices[cylinder[1], :]
        vector_c = group_vertices[cylinder[2], :]

        axis = vector_a - vector_c
        unit_axis, height = normalise(axis)
        radius = calculate_magnitude(vector_b - vector_a)
        centre = (vector_a + vector_c) * 0.5

        mesh_vertices, mesh_faces = construct_cylinder_mesh(
            height, radius, unit_axis, centre, 10
        )
        new_winding_order, new_faces = create_off_face_vertex_map(mesh_faces)
        vertices, faces, winding_order = accumulate_geometry(
            vertices, faces, winding_order, mesh_vertices, new_faces, new_winding_order
        )
    return vertices, faces, winding_order


def get_geometry_from_group(group, nexus_file):
    """
    Get geometry information from the geometry group

    :param group: Geometry group and its parent group in a dictionary
    :param nexus_file: Handle of the NeXus file input
    :return: vertices, faces and winding_order information from the group
    """
    if str(group["geometry_group"].attrs["NX_class"], "utf8") == "NXoff_geometry":
        vertices, faces, winding_order = get_off_geometry_from_group(group)
    elif (
        str(group["geometry_group"].attrs["NX_class"], "utf8")
        == "NXcylindrical_geometry"
    ):
        vertices, faces, winding_order = get_cylindrical_geometry_from_group(group)
    else:
        raise Exception(
            "nexustooff.get_geometry_from_group was passed a group which is not a geometry type"
        )
    vertices = np.matrix(vertices)
    vertices, faces, winding_order = replicate_if_pixel_geometry(
        group, vertices, faces, winding_order
    )
    vertices = get_and_apply_transformations(group, nexus_file, vertices)
    return vertices, faces, winding_order


def nexus_geometry_to_off_file(nexus_filename, off_filename):
    """
    Write all of the geometry information found in a NeXus file to an OFF file

    :param nexus_filename: Name of the NeXus file input
    :param off_filename: Name of the OFF file output
    """
    nexus_file = h5py.File(nexus_filename, "r")
    geometry_groups = find_geometry_groups(nexus_file)
    # Build up vertices, faces and winding order
    vertices = None
    faces = None
    winding_order = None
    for group in geometry_groups:
        new_vertices, new_faces, new_winding_order = get_geometry_from_group(
            group, nexus_file
        )
        vertices, faces, winding_order = accumulate_geometry(
            vertices, faces, winding_order, new_vertices, new_faces, new_winding_order
        )
    write_off_file(off_filename, vertices, faces, winding_order)


def replicate_if_pixel_geometry(group, vertices, faces, winding_order):
    """
    If the geometry group describes the shape of a single pixel then replicate the shape at all pixel offsets
    to find the shape of the whole detector panel.

    :param group: Geometry group and its parent group in a dictionary
    :param vertices: Vertices array for the original pixel
    :param faces: Faces array for the original pixel
    :param winding_order: Winding order array for the original pixel
    :return: vertices, faces, winding_order for the geometry comprising all pixels
    """
    if group["geometry_group"].name.split("/")[-1] == "pixel_shape":
        x_offsets, y_offsets, z_offsets = get_pixel_offsets(group)
        pixel_vertices = vertices
        pixel_faces = faces
        pixel_winding_order = winding_order
        next_indices = {"vertex": 0, "face": 0, "winding_order": 0}
        number_of_pixels = len(x_offsets)
        total_num_of_vertices = number_of_pixels * pixel_vertices.shape[0]

        # Preallocate arrays
        vertices = np.empty((total_num_of_vertices, 3))
        winding_order = np.empty(
            (len(pixel_winding_order) * number_of_pixels), dtype=int
        )
        faces = np.empty((len(pixel_faces) * number_of_pixels), dtype=int)

        for pixel_number in range(number_of_pixels):
            new_vertices = np.hstack(
                (
                    pixel_vertices[:, 0] + x_offsets[pixel_number],
                    pixel_vertices[:, 1] + y_offsets[pixel_number],
                    pixel_vertices[:, 2] + z_offsets[pixel_number],
                )
            )
            (
                vertices,
                faces,
                winding_order,
                next_vertex,
            ) = accumulate_geometry_in_prealloc_arrays(
                vertices,
                faces,
                winding_order,
                new_vertices,
                pixel_faces,
                pixel_winding_order,
                next_indices,
            )
    return vertices, faces, winding_order


def get_pixel_offsets(group):
    if "x_pixel_offset" in group["parent_group"]:
        x_offsets = group["parent_group"]["x_pixel_offset"][...]
    else:
        raise Exception(
            "No x_pixel_offset found in parent group of " + group["geometry_group"].name
        )
    if "y_pixel_offset" in group["parent_group"]:
        y_offsets = group["parent_group"]["y_pixel_offset"][...]
    else:
        raise Exception(
            "No y_pixel_offset found in parent group of " + group["geometry_group"].name
        )
    if "z_pixel_offset" in group["parent_group"]:
        z_offsets = group["parent_group"]["z_pixel_offset"][...]
    else:
        z_offsets = np.zeros(x_offsets.shape)
    return x_offsets, y_offsets, z_offsets


def accumulate_geometry(
    vertices, faces, winding_order, new_vertices, new_faces, new_winding_order
):
    """
    Accumulate geometry from different groups in the NeXus file, or repeated pixels.

    :param vertices: Vertices array to accumulate in
    :param faces: Faces array to accumulate in
    :param winding_order: Winding order array to accumulate in
    :param new_vertices: (2D) New vertices to append/insert
    :param new_faces: (1D) New vertices to append
    :param new_winding_order: (1D) New winding_order to append
    """
    if faces is not None:
        faces = np.concatenate((faces, new_faces + winding_order.size))
    else:
        faces = new_faces

    if winding_order is not None:
        winding_order = np.concatenate(
            (winding_order, new_winding_order + vertices.shape[0])
        )
    else:
        winding_order = new_winding_order

    if vertices is not None:
        vertices = np.vstack((vertices, new_vertices))
    else:
        vertices = new_vertices

    return vertices, faces, winding_order


def accumulate_geometry_in_prealloc_arrays(
    vertices,
    faces,
    winding_order,
    new_vertices,
    new_faces,
    new_winding_order,
    next_indices,
):
    """
    Accumulate geometry from different groups in the NeXus file, or repeated pixels.
    Arrays are assumed to be preallocated and new data are inserted at the given index instead.

    :param vertices: Vertices array to accumulate in
    :param faces: Faces array to accumulate in
    :param winding_order: Winding order array to accumulate in
    :param new_vertices: (2D) New vertices to append/insert
    :param new_faces: (1D) New vertices to append
    :param new_winding_order: (1D) New winding_order to append
    :param next_indices: Insert new data at these indices
    """
    faces[next_indices["face"] : (next_indices["face"] + len(new_faces))] = (
        new_faces + next_indices["winding_order"]
    )

    winding_order[
        next_indices["winding_order"] : (
            next_indices["winding_order"] + len(new_winding_order)
        )
    ] = (new_winding_order + next_indices["vertex"])

    vertices[
        next_indices["vertex"] : (next_indices["vertex"] + new_vertices.shape[0]), :
    ] = new_vertices

    next_indices["face"] += len(new_faces)
    next_indices["winding_order"] += len(new_winding_order)
    next_indices["vertex"] += new_vertices.shape[0]

    return vertices, faces, winding_order, next_indices


if __name__ == "__main__":
    # Example use
    # SANS2D for example as it uses NXoff_geometry and NXcylindrical_geometry
    # NB, run example_instruments/sans2d/SANS2D_example.py from its own directory first to generate NeXus file
    output_off_file = "SANS2D.off"
    nexus_geometry_to_off_file(
        "example_instruments/sans2d/SANS_example_gzip_compress.hdf5", output_off_file
    )
