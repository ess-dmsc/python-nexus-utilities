from io import StringIO
from nexusutils.readwriteoff import parse_off_file

test_OFF_file = StringIO('OFF\n'
                         '# A cube\n'
                         '# Line below is: num_of_vertices num_of_faces num_of_edges\n'
                         '8 6 12\n'
                         '1.0   0.0   1.0\n'
                         '0.0   1.0   1.0\n'
                         '-1.0   0.0   1.0\n'
                         '# This is a comment line to test that comments don\'t cause a problem\n'
                         '0.0  -1.0   1.0\n'
                         '1.0   0.0  0.0\n'
                         '0.0   1.0  0.0\n'
                         '-1.0   0.0  0.0\n'
                         '0.0  -1.0  0.0\n'
                         '# This is a comment line to test that comments don\'t cause a problem\n'
                         '4  0 1 2 3\n'
                         '4  7 4 0 3\n'
                         '4  4 5 1 0\n'
                         '4  5 6 2 1\n'
                         '4  3 2 6 7\n'
                         '# This is a comment line to test that comments don\'t cause a problem\n'
                         '4  6 5 4 7\n')


def test_face_array_row_from_parsed_OFF_file_begins_with_number_of_vertices():
    test_OFF_file.seek(0)  # Ensure file is read from the start
    vertices, faces = parse_off_file(test_OFF_file)
    for row in faces:
        number_of_vertex_indices = len(row[1:])
        assert (row[0] == number_of_vertex_indices)


def test_each_vertex_comprises_three_coordinate_components():
    test_OFF_file.seek(0)  # Ensure file is read from the start
    vertices, faces = parse_off_file(test_OFF_file)
    for vertex in vertices:
        assert (len(vertex) == 3)


def test_outputs_contain_number_of_vertices_and_faces_specified_in_file_header():
    test_OFF_file.seek(0)  # Ensure file is read from the start
    vertices, faces = parse_off_file(test_OFF_file)
    assert (len(vertices) == 8)
    assert (len(faces) == 6)
