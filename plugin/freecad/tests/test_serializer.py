from plugin.freecad.serializer import Control, serialize_document


class BB:
    def __init__(self, x, y, z):
        self.XLength = x
        self.YLength = y
        self.ZLength = z


class Shape:
    def __init__(self, bb):
        self.BoundBox = bb


class Placement:
    class BaseC:
        def __init__(self, x, y, z):
            self.x = x
            self.y = y
            self.z = z

    def __init__(self, x, y, z):
        self.Base = Placement.BaseC(x, y, z)


class Obj:
    def __init__(self, name, shape=None, placement=None):
        self.Label = name
        self.Shape = shape
        self.Placement = placement


class Doc:
    def __init__(self, objects):
        self.Objects = objects


def test_serialize_document_with_controls_and_bbox():
    objs = [
        Obj(
            "CTRL_BUTTON_1", shape=Shape(BB(100, 50, 30)), placement=Placement(1, 2, 3)
        ),
        Obj("Body", shape=Shape(BB(120, 80, 40))),
    ]
    doc = Doc(objs)
    data = serialize_document(doc)
    assert data["overall_dimensions_mm"]["xlen"] in (100.0, 120.0)
    assert len(data["controls"]) == 1
    c = data["controls"][0]
    assert c["name"] == "CTRL_BUTTON_1"
    assert c["position_xyz"] == (1.0, 2.0, 3.0)
