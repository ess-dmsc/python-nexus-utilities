import numpy as np
import logging

logger = logging.getLogger('NeXus_Builder')


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
    while line[0] == '#':
        line = off_file.readline()
    counts = line.split()
    number_of_vertices = int(counts[0])
    # These values are also in the first line, although we don't need them:
    # number_of_faces = int(counts[1])
    # number_of_edges = int(counts[2])

    off_vertices = np.zeros((number_of_vertices, 3), dtype=float)  # preallocate
    for vertex_number in range(number_of_vertices):
        off_vertices[vertex_number, :] = np.array(off_file.readline().split()).astype(float)

    faces_lines = off_file.readlines()

    all_faces = [np.array(face_line.split()).astype(int) for face_line in faces_lines if face_line[0] != '#']
    return off_vertices, all_faces
