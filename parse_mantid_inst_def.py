import xml.etree.ElementTree


def get_pixel(xml_root, type_name):
    for type in xml_root.iter('d:type', ns):
        if type.get('name') is type_name:
            cuboid = type.find('d:cuboid')
            if cuboid:
                # I'm assuming the cuboid's edges point along the cartesian axes
                # also that the pixel "thickness" is the size in the z direction
                pass
            else:
                print('no cuboid shape found to define pixel')


root = xml.etree.ElementTree.parse('SANS2D_Definition.xml').getroot()
ns = {'d': 'http://www.mantidproject.org/IDF/1.0'}

# Our root should be the instrument
assert (root.tag == '{' + ns['d'] + '}instrument')

# Look for detector bank definition
# Any type definition with an "is" attribute of "RectangularDetector"
for type in root.iter('d:type', ns):
    if type.get('is') is 'RectangularDetector':
        pixel_type = type.get('type')
        get_pixel(pixel_type)

for component in root.findall('d:component', ns):
    print component.get('type')
    # print component.attrib
