import xml.etree.ElementTree
import numpy as np


def get_point(xml_point):
    return np.array([xml_point.get('x'), xml_point.get('y'), xml_point.get('z')])


def get_pixel(xml_root, type_name):
    for type in xml_root.iter('d:type', ns):
        if type.get('name') is type_name:
            cuboid = type.find('d:cuboid')
            if cuboid:
                lfb_point = cuboid.find('d:left-front-bottom-point')
                lft_point = cuboid.find('d:left-front-top-point')
                lbb_point = cuboid.find('d:left-back-bottom-point')
                rfb_point = cuboid.find('d:right-front-bottom-point')
                left_front_bottom = get_point(lfb_point)
                left_front_top = get_point(lft_point)
                left_back_bottom = get_point(lbb_point)
                right_front_bottom = get_point(rfb_point)
                # Assume thickness is front to back
                front_to_back = left_back_bottom - left_front_bottom
                thickness = np.sqrt(np.dot(front_to_back, front_to_back))
                # Assume x pixel size is left to right
                left_to_right = right_front_bottom - left_front_bottom
                x_pixel_size = np.sqrt(np.dot(left_to_right, left_to_right))
                # Assume y pixel size is top to bottom
                top_to_bottom = left_front_top - left_front_bottom
                y_pixel_size = np.sqrt(np.dot(top_to_bottom, top_to_bottom))
                return x_pixel_size, y_pixel_size, thickness
            else:
                print('no cuboid shape found to define pixel')
    return None, None, None


root = xml.etree.ElementTree.parse('SANS2D_Definition.xml').getroot()
ns = {'d': 'http://www.mantidproject.org/IDF/1.0'}

# Our root should be the instrument
assert (root.tag == '{' + ns['d'] + '}instrument')

# Look for detector bank definition
# Any type definition with an "is" attribute of "RectangularDetector"
for type in root.iter('d:type', ns):
    if type.get('is') is 'RectangularDetector':
        pixel_type = type.get('type')
        x_pixel_size, y_pixel_size, thickness = get_pixel(pixel_type)

for component in root.findall('d:component', ns):
    print component.get('type')
    # print component.attrib
