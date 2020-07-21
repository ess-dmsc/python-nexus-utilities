from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectGui import *
from panda3d.core import GeomVertexFormat, GeomVertexData
from panda3d.core import Geom, GeomTriangles, GeomVertexWriter
from panda3d.core import GeomNode
from panda3d.core import TextNode
from pandac.PandaModules import WindowProperties
from nexusutils.readwriteoff import parse_off_file

base = ShowBase()

# Rename window
props = WindowProperties()
props.setTitle("OFF Instrument View")
base.win.requestProperties(props)

# Move the initial camera position away from 0,0,0 so that we see something
base.trackball.node().setPos(0, 20, 0)

title = OnscreenText(
    text="F3 - toggle wireframe\nF4 - reset view",
    style=1,
    fg=(1, 1, 1, 1),
    pos=(-0.6, 0.1),
    scale=0.05,
    parent=base.a2dBottomRight,
    align=TextNode.ALeft,
)


def reset_view():
    base.trackball.node().setPos(0, 20, 0)


def faces_to_triangles(faces):
    triangles = []
    # remove the first number in each face, it is the number of vertices
    faces = [face[1:] for face in faces]
    for face in faces:
        for vertex_number in range(1, len(face) - 1):
            triangles.append([face[0], face[vertex_number], face[vertex_number + 1]])
    return triangles


def render_off_vertex_and_face_arrays(vertices, faces):
    triangles = faces_to_triangles(faces)
    format = GeomVertexFormat.getV3n3cpt2()
    vdata = GeomVertexData("from_OFF", format, Geom.UHDynamic)
    vertex = GeomVertexWriter(vdata, "vertex")
    color = GeomVertexWriter(vdata, "color")
    for vert in vertices:
        vertex.addData3(vert[0], vert[1], vert[2])
        color.addData4f(0.8, 0.8, 0.8, 0.8)
    tris = GeomTriangles(Geom.UHDynamic)
    for triangle in triangles:
        tris.addVertices(triangle[0], triangle[1], triangle[2])
    off_object = Geom(vdata)
    off_object.addPrimitive(tris)
    snode = GeomNode("off_geom")
    snode.addGeom(off_object)

    offobj = render.attachNewNode(snode)

    # Our OFF is defined with y as vertical axis, z as beam direction and x as the other horizontal axis
    # Rotate it to match panda3d's expectation of z as vertical
    offobj.setHpr(0.0, 90.0, 0.0)

    # offobj.hprInterval(20, (360, 360, 360)).loop()

    # OpenGl by default only draws "front faces" (polygons whose vertices are
    # specified CCW).
    offobj.setTwoSided(True)
    base.accept("f3", base.toggleWireframe)
    base.accept("f4", reset_view)
    base.run()


def render_off_from_file(filename):
    with open(filename) as off_file:
        vertices, faces = parse_off_file(off_file)
    render_off_vertex_and_face_arrays(vertices, faces)


if __name__ == "__main__":
    render_off_from_file("example_instruments/sans2d/teapot.off")
