from io import StringIO
import numpy as np


def dict_compare(d1, d2):
    """
    Return True if the two dictionaries are equal,
    supports values containing numpy arrays

    :param d1: first dictionary
    :param d2: second dictionary
    :return: True if dictionaries are equal, False otherwise
    """
    d1_keys = set(d1.keys())
    d2_keys = set(d2.keys())
    intersect_keys = d1_keys.intersection(d2_keys)
    same = set(o for o in intersect_keys if np.array_equal(np.array(d1[o]), np.array(d2[o])))
    return (len(d1_keys) == len(d2_keys)) and (len(d1_keys) == len(same))


def create_fake_idf_file(instrument_name='TEST', source_name=None, sample=None, defaults=None, monitor_name=None,
                         structured_detector=None):
    """
    Create a fake IDF, in-memory, file object for use in unit tests of the IDF parser

    :param instrument_name: A name for the instrument
    :param source_name: A name for the source
    :param sample: Dictionary with "name" and "position" of the sample
    :param defaults: Dictionary with "length_units" and "angle_units"
    :param monitor_name: A name for a monitor
    :param structured_detector: Dictionary with "name" and "type" for a structured detector
    :return: Python file object
    """
    fake_idf_file = StringIO()

    # instrument
    fake_idf_file.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                        '<instrument xmlns="http://www.mantidproject.org/IDF/1.0" '
                        'name="' + instrument_name + '">\n')

    if source_name is not None:
        __write_source(fake_idf_file, source_name)
    if sample is not None:
        __write_sample(fake_idf_file, sample)
    if defaults is not None:
        __write_defaults(defaults, fake_idf_file)
    if monitor_name is not None:
        __write_monitors(fake_idf_file, monitor_name)
    if structured_detector is not None:
        __write_structured_detector(fake_idf_file, structured_detector)

    fake_idf_file.write('</instrument>\n')
    fake_idf_file.seek(0)  # So that the xml parser reads from the start of the file
    return fake_idf_file


def __write_structured_detector(fake_idf_file, structured_detector):
    fake_idf_file.write(
        '<component name ="' + structured_detector['name'] + '" type="' + structured_detector[
            'type'] + '" idstart="0" idfillbyfirst="x" idstepbyrow="1" idstep="2">\n'
                      '  <location x="0" y="0.01" z=" 9.23"/>\n'
                      '</component>')
    fake_idf_file.write('<type name="' + structured_detector['type'] +
                        '" is="StructuredDetector" xpixels="3" ypixels="2" type="pixel">\n')
    for vertex in structured_detector['vertices']:
        fake_idf_file.write('  <vertex x="' + str(vertex[0]) + '" y="' + str(vertex[1]) + '" />\n')
    fake_idf_file.write('  </type>\n'
                        '<type is="detector" name="pixel"/>')


def __write_monitors(fake_idf_file, monitor_name):
    fake_idf_file.write('<component type="monitors" idlist="monitors"><location/></component>\n')
    fake_idf_file.write('<type name="monitors"><component type="monitor-tbd">'
                        '<location z="7.217" name="' + monitor_name + '"/></component></type>\n')
    fake_idf_file.write('<type name="monitor-tbd" is="monitor"><cylinder id="some-shape"><centre-of-bottom-base '
                        'r="0.0" t="0.0" p="0.0" /><axis x="0.0" y="0.0" z="1.0" /> <radius val="0.01" />'
                        '<height val="0.03" /></cylinder></type>\n')
    fake_idf_file.write('<idlist idname="monitors"><id start="1" end="1" /></idlist>\n')


def __write_defaults(defaults, fake_idf_file):
    fake_idf_file.write('<defaults><length unit="' + defaults['length_units'] + '"/><angle unit="' + defaults[
        'angle_units'] + '"/><reference-frame><along-beam axis="z"/>'
                         '<pointing-up axis="y"/><handedness val="right"/></reference-frame></defaults>\n')


def __write_sample(fake_idf_file, sample):
    fake_idf_file.write(
        '<component type="' + sample['name'] + '"><location x="' + str(sample['position'][0]) + '" y="' + str(
            sample['position'][1]) + '" z="' + str(sample['position'][2]) + '"/></component>')
    fake_idf_file.write('<type name="' + sample['name'] + '" is="SamplePos"/>\n')


def __write_source(fake_idf_file, source_name):
    fake_idf_file.write('<type name="' + source_name + '" is="Source"></type>\n')
    fake_idf_file.write('<component type="' + source_name + '"><location z="-40.0"/></component>\n')
