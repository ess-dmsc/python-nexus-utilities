import numpy as np
import logging

logger = logging.getLogger('NeXus_Utils')


def parse_off_file(off_file):
    """
    Read vertex list and face definitions from an OFF file and return as lists of numpy arrays

    :param off_file: File object assumed to contain geometry description in OFF format
    :return: List of vertices and list of vertex indices in each face
    """
    file_start = off_file.readline()
    if file_start != 'OFF\n':
        logger.error('OFF file is expected to start "OFF", actually started: ' + file_start)
        return None
    line = off_file.readline()
    # Skip any comment lines
    while line[0] == '#' or line == '\n':
        line = off_file.readline()
    counts = line.split()
    number_of_vertices = int(counts[0])
    # These values are also in the first line, although we don't need them:
    # number_of_faces = int(counts[1])
    # number_of_edges = int(counts[2])

    off_vertices = np.zeros((number_of_vertices, 3), dtype=float)  # preallocate
    vertex_number = 0
    while vertex_number < number_of_vertices:
        line = off_file.readline()
        if line[0] != '#' and line != '\n':
            off_vertices[vertex_number, :] = np.array(line.split()).astype(float)
            vertex_number += 1

    faces_lines = off_file.readlines()
    # Only keep the first value (number of vertex indices in face) plus the number of vertices.
    # There may be other numbers following it to define a colour for the face, which we don't want to keep
    all_faces = [np.array(face_line.split()[:(int(face_line.split()[0]) + 1)]).astype(int) for face_line in faces_lines
                 if face_line[0] != '#']
    return off_vertices, all_faces


def write_off_file(filename, vertices, faces, winding_order):
    """
    Create an OFF format file

    :param filename: Name for the OFF file to output
    :param vertices: 2D array contains x, y, z coords for each vertex
    :param faces: 1D array indexing into winding_order at the start of each face
    :param winding_order: 1D array of vertex indices in the winding order for each face
    """
    number_of_vertices = len(vertices)
    number_of_faces = len(faces) - 1
    # According to OFF standard the number of edges must be present but does not need to be correct
    number_of_edges = 0
    with open(filename, 'wb') as off_file:
        off_file.write('OFF\n'.encode('utf8'))
        off_file.write('# NVertices NFaces NEdges\n'.encode('utf8'))
        off_file.write('{} {} {}\n'.format(number_of_vertices, number_of_faces, number_of_edges).encode('utf8'))

        off_file.write('# Vertices\n'.encode('utf8'))
        np.savetxt(off_file, vertices, fmt='%f', delimiter=" ")

        off_file.write('# Faces\n'.encode('utf8'))
        previous_index = 0
        for face in faces[1:]:
            verts_in_face = winding_order[previous_index:face]
            fmt_str = '{} ' * (len(verts_in_face) + 1)
            fmt_str = fmt_str[:-1] + '\n'
            off_file.write(fmt_str.format(len(verts_in_face), *verts_in_face).encode('utf8'))
            previous_index = face
