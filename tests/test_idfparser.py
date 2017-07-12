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
    monitors = {'name': 'TEST_MONITOR'}
    fake_idf_file = create_fake_idf_file(monitors=monitors)
    parser = IDFParser(fake_idf_file)
    monitors_out, monitor_types = parser.get_monitors()
    assert monitors_out[0]['name'] == monitors['name']
    fake_idf_file.close()


def test_get_structured_detectors():
    expected_output = {'type_name': 'fan', 'orientation': None, 'Y_id_step': 2, 'location': np.array([0., 0.01, 9.23]),
                       'id_start': 0, 'X_id_step': 1, 'name': 'TEST_STRUCT_DET'}
    fake_idf_file = create_fake_idf_file(structured_detector_name=expected_output['name'])
    parser = IDFParser(fake_idf_file)
    for detector in parser.get_structured_detectors():
        assert dict_compare(expected_output, detector)
    fake_idf_file.close()
