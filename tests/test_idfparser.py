import pytest
import numpy as np
import operator
from nexusutils.idfparser import IDFParser, NotFoundInIDFError, UnknownPixelShapeError
from .idfhelper import create_fake_idf_file, dict_compare


def test_get_instrument_name_returns_name_specified_in_IDF():
    instrument_name = 'TEST_NAME'
    fake_idf_file = create_fake_idf_file(instrument_name)
    parser = IDFParser(fake_idf_file)
    assert parser.get_instrument_name() == instrument_name
    fake_idf_file.close()


def test_get_source_name_returns_name_specified_in_IDF():
    name = 'TEST_SOURCE'
    fake_idf_file = create_fake_idf_file(source_name=name)
    parser = IDFParser(fake_idf_file)
    assert parser.get_source_name() == name
    fake_idf_file.close()


def test_get_source_name_returns_none_if_no_name_specified_in_IDF():
    fake_idf_file = create_fake_idf_file()
    parser = IDFParser(fake_idf_file)
    assert parser.get_source_name() is None
    fake_idf_file.close()


def test_sample_position_is_at_origin():
    sample_pos = [-0.54, 42.0, 0.48]
    source_pos = [0.0, 0.0, -40, 0]  # hardcoded in fake idf
    test_sample = {'name': 'TEST_SAMPLE',
                   'position': sample_pos}
    fake_idf_file = create_fake_idf_file(sample=test_sample, source_name="the_source")
    parser = IDFParser(fake_idf_file)
    np.testing.assert_allclose(parser.get_sample_position(), np.array([0., 0., 0.]))
    # Check that source is offset from IDF into nexus frame
    np.testing.assert_allclose(parser.get_source_position(), np.array(list(map(operator.sub, source_pos, sample_pos))))
    fake_idf_file.close()


def test_get_sample_position_fails_when_no_samplePos_in_IDF():
    fake_idf_file = create_fake_idf_file()
    parser = IDFParser(fake_idf_file)
    with pytest.raises(NotFoundInIDFError):
        parser.get_sample_position()
    fake_idf_file.close()


def test_get_length_units_returns_same_length_unit_string_as_specified_in_IDF():
    test_defaults = {'length_units': 'cubits',
                     'angle_units': 'deg'}
    fake_idf_file = create_fake_idf_file(defaults=test_defaults)
    parser = IDFParser(fake_idf_file)
    assert parser.get_length_units() == test_defaults['length_units']
    fake_idf_file.close()


def test_get_angle_units_returns_deg_when_specified_as_deg_in_IDF():
    test_defaults = {'length_units': 'Yojana',
                     'angle_units': 'deg'}
    fake_idf_file = create_fake_idf_file(defaults=test_defaults)
    parser = IDFParser(fake_idf_file)
    assert parser.get_angle_units() == test_defaults['angle_units']
    fake_idf_file.close()


def test_get_angle_unit_on_other_than_rad_or_deg_fails():
    test_defaults = {'length_units': 'Ald',
                     'angle_units': 'Furman'}
    fake_idf_file = create_fake_idf_file(defaults=test_defaults)
    with pytest.raises(ValueError):
        IDFParser(fake_idf_file)
    fake_idf_file.close()


def test_get_monitors_retrieves_monitor_with_name_specified_in_IDF():
    monitor_name = 'TEST_MONITOR'
    fake_idf_file = create_fake_idf_file(monitor_name=monitor_name)
    parser = IDFParser(fake_idf_file)
    monitors_out, monitor_types = parser.get_monitors()
    assert monitors_out[0]['name'] == monitor_name
    fake_idf_file.close()


def test_get_structured_detectors_returns_detector_details():
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


def test_get_structured_detector_vertices_returns_coords_specified_in_IDF():
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


def test_get_detectors_throws_when_pixel_shape_is_unknown():
    pixel = {'shape': {'shape': 'lumpy'}, 'name': 'potato'}
    detector = {'pixel': pixel}
    fake_idf_file = create_fake_idf_file(detector=detector)
    parser = IDFParser(fake_idf_file)
    with pytest.raises(UnknownPixelShapeError):
        parser.get_detectors()
    fake_idf_file.close()


def test_get_detectors_returns_detector_details_for_tube_pixels():
    pixel = {'name': 'pixel',
             'shape': {'shape': 'cylinder', 'axis': np.array([0.0, 1.0, 0.0]), 'height': 0.2, 'radius': 0.1}}
    detector = {'pixel': pixel}
    fake_idf_file = create_fake_idf_file(detector=detector)
    parser = IDFParser(fake_idf_file)
    output_detectors = parser.get_detectors()
    assert dict_compare(output_detectors[0]['pixel']['shape'], pixel['shape'])
    fake_idf_file.close()


def test_get_detectors_returns_detector_details_for_cuboid_pixels():
    pixel = {'name': 'pixel',
             'shape': {'shape': 'cuboid', 'x_pixel_size': 0.01, 'y_pixel_size': 0.01, 'thickness': 0.005}}
    detector = {'pixel': pixel}
    fake_idf_file = create_fake_idf_file(detector=detector)
    parser = IDFParser(fake_idf_file)
    output_detectors = parser.get_detectors()
    assert dict_compare(output_detectors[0]['pixel']['shape'], pixel['shape'])
    fake_idf_file.close()


def test_get_rectangular_detectors_returns_detector_details():
    pixel = {'name': 'pixel',
             'shape': {'shape': 'cuboid', 'x_pixel_size': 0.01, 'y_pixel_size': 0.01, 'thickness': 0.005}}
    detector = {'pixel': pixel, 'xstart': -0.4, 'xstep': 0.4, 'xpixels': 3, 'ystart': -0.4, 'ystep': 0.4, 'ypixels': 3,
                'idstart': 2000000, 'idstep': 1000}
    fake_idf_file = create_fake_idf_file(rectangular_detector=detector)
    parser = IDFParser(fake_idf_file)
    output_detectors = list(parser.get_rectangular_detectors())
    assert dict_compare(output_detectors[0]['pixel']['shape'], pixel['shape'])
    fake_idf_file.close()


def test_get_rectangular_detectors_returns_expected_pixel_offsets():
    pixel = {'name': 'pixel',
             'shape': {'shape': 'cuboid', 'x_pixel_size': 0.01, 'y_pixel_size': 0.01, 'thickness': 0.005}}
    detector = {'pixel': pixel, 'xstart': -0.4, 'xstep': 0.4, 'xpixels': 3, 'ystart': -0.4, 'ystep': 0.4, 'ypixels': 3,
                'idstart': 2000000, 'idstep': 1000}
    fake_idf_file = create_fake_idf_file(rectangular_detector=detector)
    parser = IDFParser(fake_idf_file)
    output_detectors = list(parser.get_rectangular_detectors())
    expected_x_offsets = np.linspace(detector['xstart'],
                                     detector['xstart'] + (detector['xstep'] * (detector['xpixels'] - 1)),
                                     detector['xpixels'])
    expected_y_offsets = np.linspace(detector['ystart'],
                                     detector['ystart'] + (detector['ystep'] * (detector['ypixels'] - 1)),
                                     detector['ypixels'])
    assert np.allclose(expected_x_offsets, output_detectors[0]['offsets'][0, :, 0])
    assert np.allclose(expected_y_offsets, output_detectors[0]['offsets'][:, 0, 1])


def test_get_rectangular_detectors_returns_expected_ids():
    pixel = {'name': 'pixel',
             'shape': {'shape': 'cuboid', 'x_pixel_size': 0.01, 'y_pixel_size': 0.01, 'thickness': 0.005}}
    detector = {'pixel': pixel, 'xstart': -0.4, 'xstep': 0.4, 'xpixels': 3, 'ystart': -0.4, 'ystep': 0.4, 'ypixels': 3,
                'idstart': 2000000, 'idstep': 1000}
    fake_idf_file = create_fake_idf_file(rectangular_detector=detector)
    parser = IDFParser(fake_idf_file)
    output_detectors = list(parser.get_rectangular_detectors())
    expected_ids = np.array([[detector['idstart'], detector['idstart'] + detector['idstep'],
                              detector['idstart'] + (detector['idstep'] * 2)],
                             [detector['idstart'] + 1, detector['idstart'] + detector['idstep'] + 1,
                              detector['idstart'] + (detector['idstep'] * 2) + 1],
                             [detector['idstart'] + 2, detector['idstart'] + detector['idstep'] + 2,
                              detector['idstart'] + (detector['idstep'] * 2) + 2]]).astype(int)
    assert np.array_equal(expected_ids, output_detectors[0]['idlist'])


def test_rectangular_detectors_have_default_id_parameters():
    pixel = {'name': 'pixel',
             'shape': {'shape': 'cuboid', 'x_pixel_size': 0.01, 'y_pixel_size': 0.01, 'thickness': 0.005}}
    detector = {'pixel': pixel, 'xstart': -0.4, 'xstep': 0.4, 'xpixels': 3, 'ystart': -0.4, 'ystep': 0.4, 'ypixels': 3}
    fake_idf_file = create_fake_idf_file(rectangular_detector=detector)
    parser = IDFParser(fake_idf_file)
    output_detectors = list(parser.get_rectangular_detectors())
    default_idstart = 1
    default_idstep = 1
    expected_ids = np.array([[default_idstart, default_idstart + default_idstep,
                              default_idstart + (default_idstep * 2)],
                             [default_idstart + 1, default_idstart + default_idstep + 1,
                              default_idstart + (default_idstep * 2) + 1],
                             [default_idstart + 2, default_idstart + default_idstep + 2,
                              default_idstart + (default_idstep * 2) + 2]]).astype(int)
    assert np.array_equal(expected_ids, output_detectors[0]['idlist'])
