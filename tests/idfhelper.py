from io import StringIO
import numpy as np

"""
Helper functions for IDFParser unit tests
"""


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
                         structured_detector=None, detector=None, rectangular_detector=None, custom_location=None):
    """
    Create a fake IDF, in-memory, file object for use in unit tests of the IDF parser

    :param instrument_name: A name for the instrument
    :param source_name: A name for the source
    :param sample: Dictionary with "name" and "position" of the sample
    :param defaults: Dictionary with "length_units" and "angle_units"
    :param monitor_name: A name for a monitor
    :param structured_detector: Dictionary with "name" and "type" for a structured detector
    :param detector: Dictionary with pixel and detector component information
    :param rectuangular_detector: Dictionary with parameters for a rectangular detector
    :param custom_location: Custom location element for a component
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
    if detector is not None:
        __write_detector(fake_idf_file, detector)
    if rectangular_detector is not None:
        __write_rectangular_detector(fake_idf_file, rectangular_detector, custom_location)

    fake_idf_file.write('</instrument>\n')
    fake_idf_file.seek(0)  # So that the xml parser reads from the start of the file
    return fake_idf_file


def __write_rectangular_detector(fake_idf_file, detector, custom_location):
    __write_detector_pixel(fake_idf_file, detector['pixel'])
    __write_rectangular_detector_type(fake_idf_file, detector)
    __write_rectangular_detector_component(fake_idf_file, detector, custom_location)


def __write_rectangular_detector_type(fake_idf_file, detector):
    fake_idf_file.write('  <type name="detector-bank" is="rectangular_detector" type="pixel"\n'
                        '    xpixels="' + str(detector['xpixels']) + '" xstart="' + str(detector['xstart']) +
                        '" xstep="' + str(detector['xstep']) + '"\n'
                                                               '    ypixels="' +
                        str(detector['ypixels']) + '" ystart="' + str(detector['ystart']) +
                        '" ystep="' + str(detector['ystep']) + '" >\n'
                                                               '  </type>\n')


def __write_rectangular_detector_component(fake_idf_file, detector, custom_location=None):
    if not custom_location:
        location = r'<location x="2.1" z="23.281" name="front-detector"/>'
    else:
        location = custom_location

    if 'idstart' in detector.keys() and 'idstep' in detector.keys():
        fake_idf_file.write(
            '  <component type="detector-bank" idstart="' + str(
                detector['idstart']) + '" idfillbyfirst="y" idstep="' + str(detector['idstep']) +
            '" idstepbyrow="1">\n'
            f'  {location}\n'  
            '  </component>\n')
    else:
        fake_idf_file.write(
            '  <component type="detector-bank">\n'
            f'    {location}\n'
            '  </component>\n')


def __write_detector(fake_idf_file, detector):
    __write_detector_pixel(fake_idf_file, detector['pixel'])
    __write_detector_component(fake_idf_file, detector['pixel']['name'])
    __write_detector_panel(fake_idf_file)
    __write_idlist(fake_idf_file)


def __write_idlist(fake_idf_file):
    fake_idf_file.write('<idlist idname="test-idlist">\n'
                        '  <id start="1" end="3" />\n'
                        '</idlist>\n')


def __write_detector_panel(fake_idf_file):
    fake_idf_file.write('<component type="small-detector" idlist="test-idlist" name="panel01">\n'
                        '  <location  x="-0.42" z="1.97" name="panel01" > <facing x="0" y="0" z="0"/> </location>\n'
                        '</component>\n')


def __write_detector_component(fake_idf_file, pixel_name):
    fake_idf_file.write('<type name="small-detector">\n'
                        '  <component type="' + pixel_name + '">\n'
                                                             '    <location y="-0.1" name="pixel0001"/>\n'
                                                             '    <location y="0.0"  name="pixel0002"/>\n'
                                                             '    <location y="0.1"  name="pixel0003"/>\n'
                                                             '  </component>\n'
                                                             '</type>\n')


def __write_detector_pixel(fake_idf_file, pixel):
    fake_idf_file.write('<type name="' + pixel['name'] + '" is="detector">\n'
                        + __create_pixel_shape(pixel['shape']) +
                        '</type>\n')


def __create_pixel_shape(pixel_shape):
    if pixel_shape['shape'] == 'cylinder':
        return ('  <cylinder id="cyl-approx">\n'
                '    <centre-of-bottom-base r="0.0" t="0.0" p="0.0" />\n'
                '    <axis x="' + str(pixel_shape['axis'][0]) + '" y="' + str(pixel_shape['axis'][1]) +
                '" z="' + str(pixel_shape['axis'][2]) + '" />\n'
                                                        '    <radius val="' +
                str(pixel_shape['radius']) + '" />\n'
                                             '    <height val="' + str(pixel_shape['height']) + '" />\n'
                                                                                                '  </cylinder>\n')
    if pixel_shape['shape'] == 'cuboid':
        return ('  <cuboid id="shape">'
                '    <left-front-bottom-point x="' + str(pixel_shape['x_pixel_size'] / 2.) + '" y="' +
                str(pixel_shape['y_pixel_size'] / -2.) +
                '" z="' + str(0.0) + '"  />'
                                     '    <left-front-top-point  x="' +
                str(pixel_shape['x_pixel_size'] / 2.) + '" y="' +
                str(pixel_shape['y_pixel_size'] / -2.) + '" z="' +
                str(pixel_shape['thickness']) + '"  />'
                                                '    <left-back-bottom-point  x="' +
                str(pixel_shape['x_pixel_size'] / -2.) + '" y="' +
                str(pixel_shape['y_pixel_size'] / -2.) + '" z="' +
                str(0.0) + '"  />'
                           '    <right-front-bottom-point  x="' +
                str(pixel_shape['x_pixel_size'] / 2.) + '" y="' +
                str(pixel_shape['y_pixel_size'] / 2.) + '" z="' +
                str(0.0) + '"  />'
                           '  </cuboid>')

    return '<' + pixel_shape['shape'] + '></' + pixel_shape['shape'] + '>\n'


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
