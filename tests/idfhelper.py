from io import StringIO


def create_fake_idf_file(instrument_name='TEST', source_name=None, sample=None, defaults=None, monitors=None,
                         structured_detector_name=None):
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
    if monitors is not None:
        __write_monitors(fake_idf_file, monitors)
    if structured_detector_name is not None:
        __write_structured_detector(fake_idf_file, structured_detector_name)

    fake_idf_file.write('</instrument>\n')
    fake_idf_file.seek(0)  # So that the xml parser reads from the start of the file
    return fake_idf_file


def __write_structured_detector(fake_idf_file, structured_detector_name):
    fake_idf_file.write(
        '<component name ="' + structured_detector_name + '" type="fan" idstart="0" idfillbyfirst="x" idstepbyrow="1" '
                                                          'idstep="2">\n'
                                                          '  <location x="0" y="0.01" z=" 9.23"/>\n'
                                                          '</component>')
    fake_idf_file.write('<type name="fan" is="StructuredDetector" xpixels="3" ypixels="2" type="pixel">\n'
                        '  <vertex x="-2.0" y="1.0" />\n'
                        '  <vertex x="-1.0" y="1.0" />\n'
                        '  <vertex x="1.0" y="1.0" />\n'
                        '  <vertex x="2.0" y="1.0" />\n'
                        '  <vertex x="-1.0" y="0.0" />\n'
                        '  <vertex x="-0.5" y="0.0" />\n'
                        '  <vertex x="0.5" y="0.0" />\n'
                        '  <vertex x="1.0" y="0.0" />\n'
                        '  <vertex x="-0.5" y="-1.0" />\n'
                        '  <vertex x="-0.25" y="-1.0" />\n'
                        '  <vertex x="0.25" y="-1.0" />\n'
                        '  <vertex x="0.5" y="-1.0" />\n'
                        '  </type>\n'
                        '<type is="detector" name="pixel"/>')


def __write_monitors(fake_idf_file, monitors):
    fake_idf_file.write('<component type="monitors" idlist="monitors"><location/></component>\n')
    fake_idf_file.write('<type name="monitors"><component type="monitor-tbd">'
                        '<location z="7.217" name="' + monitors['name'] + '"/></component></type>\n')
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
