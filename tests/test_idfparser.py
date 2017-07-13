import env
import pytest
import numpy as np
from idfparser import IDFParser
from idfhelper import create_fake_idf_file, dict_compare


def test_get_instrument_name():
    instrument_name = 'TEST_NAME'
    fake_idf_file = create_fake_idf_file(instrument_name)
    parser = IDFParser(fake_idf_file)
    assert parser.get_instrument_name() == instrument_name
    fake_idf_file.close()


def test_get_source_name():
    name = 'TEST_SOURCE'
    fake_idf_file = create_fake_idf_file(source_name=name)
    parser = IDFParser(fake_idf_file)
    assert parser.get_source_name() == name
    fake_idf_file.close()


def test_get_sample_position():
    test_sample = {'name': 'TEST_SAMPLE',
                   'position': [-0.54, 42.0, 0.48]}
    fake_idf_file = create_fake_idf_file(sample=test_sample)
    parser = IDFParser(fake_idf_file)
    np.testing.assert_allclose(parser.get_sample_position(), test_sample['position'])
    fake_idf_file.close()


def test_get_length_units():
    test_defaults = {'length_units': 'cubits',
                     'angle_units': 'deg'}
    fake_idf_file = create_fake_idf_file(defaults=test_defaults)
    parser = IDFParser(fake_idf_file)
    assert parser.get_length_units() == test_defaults['length_units']
    fake_idf_file.close()


def test_get_angle_units():
    test_defaults = {'length_units': 'Yojana',
                     'angle_units': 'deg'}
    fake_idf_file = create_fake_idf_file(defaults=test_defaults)
    parser = IDFParser(fake_idf_file)
    assert parser.get_angle_units() == test_defaults['angle_units']
    fake_idf_file.close()


def test_angle_unit_other_than_rad_or_deg_fails():
    test_defaults = {'length_units': 'Ald',
                     'angle_units': 'Furman'}
    fake_idf_file = create_fake_idf_file(defaults=test_defaults)
    with pytest.raises(ValueError, message="Expecting ValueError for unexpected angle unit"):
        IDFParser(fake_idf_file)
    fake_idf_file.close()


def test_get_monitors():
    monitor_name = 'TEST_MONITOR'
    fake_idf_file = create_fake_idf_file(monitor_name=monitor_name)
    parser = IDFParser(fake_idf_file)
    monitors_out, monitor_types = parser.get_monitors()
    assert monitors_out[0]['name'] == monitor_name
    fake_idf_file.close()


def test_get_structured_detectors():
    x_pos = np.hstack((np.linspace(-3., 3., 4), np.linspace(-1.5, 1.5, 4), np.linspace(-0.3, 0.3, 4)))
    y_pos = np.hstack(np.array([[1.] * 4, [0.] * 4, [-1.] * 4]))
    z_pos = np.array([0.] * 12)
    input_vertices = np.hstack((np.expand_dims(x_pos, 1), np.expand_dims(y_pos, 1), np.expand_dims(z_pos, 1)))
    expected_output = {'type_name': 'fan', 'orientation': None, 'Y_id_step': 2, 'location': np.array([0., 0.01, 9.23]),
                       'id_start': 0, 'X_id_step': 1, 'name': 'TEST_STRUCT_DET'}
    fake_idf_file = create_fake_idf_file(structured_detector={'name': expected_output['name'],
                                                              'type': expected_output['type_name'],
                                                              'vertices': input_vertices})
    parser = IDFParser(fake_idf_file)
    for detector in parser.get_structured_detectors():
        assert dict_compare(expected_output, detector)
    fake_idf_file.close()


def test_get_structured_detector_vertices():
    x_pos = np.hstack((np.linspace(-3., 3., 4), np.linspace(-1.5, 1.5, 4), np.linspace(-0.3, 0.3, 4)))
    y_pos = np.hstack(np.array([[1.] * 4, [0.] * 4, [-1.] * 4]))
    z_pos = np.array([0.] * 12)
    input_vertices = np.hstack((np.expand_dims(x_pos, 1), np.expand_dims(y_pos, 1), np.expand_dims(z_pos, 1)))
    detector = {'name': 'TEST_STRUCT_DET', 'type': 'fan', 'vertices': input_vertices}
    fake_idf_file = create_fake_idf_file(structured_detector=detector)
    parser = IDFParser(fake_idf_file)
    output_vertices = parser.get_structured_detector_vertices(detector['type'])

    reshaped_input = np.reshape(input_vertices, (4, 3, 3), order='F')
    assert np.allclose(reshaped_input, output_vertices)
    fake_idf_file.close()


def test_get_detectors_unknown_pixel_shape():
    pixel = {'shape': {'shape': 'lumpy'}, 'name': 'potato'}
    detector = {'pixel': pixel}
    fake_idf_file = create_fake_idf_file(detector=detector)
    parser = IDFParser(fake_idf_file)
    with pytest.raises(Exception):
        parser.get_detectors()
    fake_idf_file.close()


def test_get_detectors():
    pixel = {'name': 'pixel',
             'shape': {'shape': 'cylinder', 'axis': np.array([0.0, 1.0, 0.0]), 'height': 0.2, 'radius': 0.1}}
    detector = {'pixel': pixel}
    fake_idf_file = create_fake_idf_file(detector=detector)
    parser = IDFParser(fake_idf_file)
    output_detectors = parser.get_detectors()
    assert output_detectors
    fake_idf_file.close()


def test_get_detectors_tubes():
    pixel = {'name': 'pixel',
             'shape': {'shape': 'cylinder', 'axis': np.array([0.0, 1.0, 0.0]), 'height': 0.2, 'radius': 0.1}}
    detector = {'pixel': pixel}
    fake_idf_file = create_fake_idf_file(detector=detector)
    parser = IDFParser(fake_idf_file)
    output_detectors = parser.get_detectors()
    assert dict_compare(output_detectors[0]['pixel']['shape'], pixel['shape'])
    fake_idf_file.close()
