from typing import Union, List

from boxes import Boxes
from boxes.utils import argparseSections
from xml.sax.saxutils import quoteattr
import boxes.edges as edges
from boxes.utils import edge_init

nema_sizes = {
    #    motor,flange, holes, screws
    8: (20.3, 16, 15.4, 3),
    11: (28.2, 22, 23, 4),
    14: (35.2, 22, 26, 4),
    16: (39.2, 22, 31, 4),
    17: (42.2, 22, 31, 4),
    23: (56.4, 38.1, 47.1, 5.2),
    24: (60, 36, 49.8, 5.1),
    34: (86.3, 73, 69.8, 6.6),
    42: (110, 55.5, 89, 8.5),
}


class ArgparseEdgeType:
    """argparse type to select from a set of edge types"""

    names = edges.getDescriptions()
    edges: list[str] = []

    def __init__(self, edges: str | None = None) -> None:
        if edges is not None:
            self.edges = list(edges)

    def __call__(self, pattern):
        if len(pattern) != 1:
            raise ValueError("Edge type can only have one letter.")
        if pattern not in self.edges:
            raise ValueError(
                "Use one of the following values: " + ", ".join(self.edges)
            )
        return pattern

    def html(self, name, default, translate):
        options = "\n".join(
            """<option value="%s"%s>%s</option>"""
            % (
                e,
                ' selected="selected"' if e == default else "",
                translate("{} {}".format(e, self.names.get(e, ""))),
            )
            for e in self.edges
        )
        return """<select name="{}" id="{}" aria-labeledby="{} {}" size="1">\n{}</select>\n""".format(
            name, name, name + "_id", name + "_description", options
        )

    def inx(self, name, viewname, arg):
        return (
            '        <param name="%s" type="optiongroup" appearance="combo" gui-text="%s" gui-description=%s>\n'
            % (name, viewname, quoteattr(arg.help or ""))
            + "".join(
                '            <option value="{}">{} {}</option>\n'.format(
                    e, e, self.names.get(e, "")
                )
                for e in self.edges
            )
            + "      </param>\n"
        )


class DefaultBoxes(Boxes):
    def __init__(
        self,
        x: float = 100,
        y: float = 100,
        h: float = 100,
        sx: Union[str, List] = "50*3",
        sy: Union[str, List] = "50*3",
        sh: Union[str, List] = "50*3",
        hi: float = 0,
        hole_dD: str = "3.5:6.5",
        bottom_edge: str = "h",
        top_edge: str = "e",
        outside: bool = True,
        nema_mount: int = 23,
        thickness: float = 3,
        output: str = "box.svg",
        format: str = "svg",
        tabs: float = 0,
        qr_code: bool = False,
        debug: bool = False,
        labels: bool = True,
        reference: float = 100,
        inner_corners: str = "loop",
        burn: float = 0.1,
    ) -> None:
        self.x = x
        self.y = y
        self.h = h
        self.sx = sx
        self.sy = sy
        self.sh = sh
        self.hi = hi
        self.hole_dD = hole_dD
        self.bottom_edge = bottom_edge
        self.top_edge = top_edge
        self.outside = outside
        self.nema_mount = nema_mount
        super().__init__(
            thickness,
            output,
            format,
            tabs,
            qr_code,
            debug,
            labels,
            reference,
            inner_corners,
            burn,
        )

        for key in ("sx", "sy", "sh", "hole_dD"):
            default = getattr(self, key)
            if isinstance(default, str):
                result = argparseSections(default)
                setattr(self, key, result)
        for key, arg in {"bottom_edge": "Fhse", "top_edge": "efFhcESŠikvLtGyY"}.items():
            default = getattr(self, key)
            if isinstance(getattr(self, key), str):
                result = ArgparseEdgeType(arg)(default)
                setattr(self, key, result)
        if nema_mount not in nema_sizes:
            raise Exception(
                f"Problem with nema_mount, needed {list(nema_sizes.keys())}"
            )


class _TopEdge(DefaultBoxes):
    def addTopEdgeSettings(
        self,
        fingerjoint={},
        stackable={},
        hinge={},
        cabinethinge={},
        slideonlid={},
        click={},
        roundedtriangle={},
        mounting={},
        handle={},
    ):
        edge_init(
            self,
            [
                {"settings": edges.FingerJointSettings, "args": fingerjoint},
                {"settings": edges.StackableSettings, "args": stackable},
                {"settings": edges.HingeSettings, "args": hinge},
                {"settings": edges.CabinetHingeSettings, "args": cabinethinge},
                {"settings": edges.SlideOnLidSettings, "args": slideonlid},
                {"settings": edges.ClickSettings, "args": click},
                {
                    "settings": edges.RoundedTriangleEdgeSettings,
                    "args": roundedtriangle,
                },
                {"settings": edges.MountingSettings, "args": mounting},
                {"settings": edges.HandleEdgeSettings, "args": handle},
            ],
        )

    def topEdges(self, top_edge):
        """Return top edges belonging to given main edge type
        as a list containing edge for left, back, right, front.
        """
        tl = tb = tr = tf = self.edges.get(top_edge, self.edges["e"])
        check_square = tl.char

        if check_square == "i":
            tb = tf = "e"
            tl = "j"
        elif check_square == "k":
            tl = tr = "e"
        elif check_square == "L":
            tl, tf, tr = "M", "e", "N"
        elif check_square == "v":
            tl = tr = tf = "e"
        elif check_square == "t":
            tf = tb = "e"
        elif check_square == "G":
            tl = tb = tr = tf = "e"
            side = self.edges[tl.char].settings.side
            if side == edges.MountingSettings.PARAM_LEFT:
                tl = "G"
            elif side == edges.MountingSettings.PARAM_RIGHT:
                tr = "G"
            elif side == edges.MountingSettings.PARAM_FRONT:
                tf = "G"
            else:  # PARAM_BACK
                tb = "G"
        elif check_square == "y":
            tl = tb = tr = tf = "e"
            if self.edges[check_square].settings.on_sides is True:
                tl = tr = "y"
            else:
                tb = tf = "y"
        elif check_square == "Y":
            tl = tb = tr = tf = "h"
            if self.edges["Y"].settings.on_sides is True:
                tl = tr = "Y"
            else:
                tb = tf = "Y"
        return [tl, tb, tr, tf]

    def drawLid(self, x, y, top_edge, bedBolts=[None, None]):
        d2, d3 = bedBolts
        if top_edge == "c":
            self.rectangularWall(
                x, y, "CCCC", bedBolts=[d2, d3, d2, d3], move="up", label="top"
            )
        elif top_edge == "f":
            self.rectangularWall(x, y, "FFFF", move="up", label="top")
        elif top_edge in "FhŠY":
            self.rectangularWall(x, y, "ffff", move="up", label="top")
        elif top_edge == "L":
            self.rectangularWall(x, y, "Enlm", move="up", label="lid top")
        elif top_edge == "i":
            self.rectangularWall(x, y, "EJeI", move="up", label="lid top")
        elif top_edge == "k":
            outset = self.edges["k"].settings.outset
            self.edges["k"].settings.setValues(self.thickness, outset=True)
            lx = x / 2.0 - 0.1 * self.thickness
            self.edges["k"].settings.setValues(self.thickness, grip_length=5)
            self.rectangularWall(lx, y, "IeJe", move="right", label="lid top left")
            self.rectangularWall(lx, y, "IeJe", move="mirror up", label="lid top right")
            self.rectangularWall(lx, y, "IeJe", move="left only", label="invisible")
            self.edges["k"].settings.setValues(self.thickness, outset=outset)
        elif top_edge == "v":
            self.rectangularWall(x, y, "VEEE", move="up", label="lid top")
            self.edges["v"].parts(move="up")
        else:
            return False
        return True
