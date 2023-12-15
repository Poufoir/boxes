# Copyright (C) 2013-2017 Florian Festi
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

from typing import List
from boxes import edges
from boxes.utils import edge_init
from boxes.lids import _TopEdge, LidSettings
import math


class UBox(_TopEdge):
    """Box various options for different stypes and lids"""

    ui_group = "FlexBox"

    def __init__(
        self,
        x: float = 100,
        y: float = 100,
        h: float = 100,
        sx: str | List = "50*3",
        sy: str | List = "50*3",
        sh: str | List = "50*3",
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
        radius: float = 30,
        angle: float = 0,
    ) -> None:
        super().__init__(
            x,
            y,
            h,
            sx,
            sy,
            sh,
            hi,
            hole_dD,
            bottom_edge,
            top_edge,
            outside,
            nema_mount,
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
        self.addTopEdgeSettings()
        edge_init(self, [edges.FlexSettings, LidSettings])
        # radius of bottom corners
        self.radius = radius
        self.angle = angle

    def U(self, x, y, r, edge="e", move=None, label=""):
        e = self.edges.get(edge, edge)

        w = self.edges["f"].spacing()
        tw = x + 2 * w
        th = y + w + e.spacing()
        if self.move(tw, th, move, True, label=label):
            return

        self.moveTo(w + r, w)
        self.edges["f"](x - 2 * r)
        self.corner(90, r)
        self.edges["f"](y - r)
        self.edgeCorner("f", e)
        e(x)
        self.edgeCorner(e, "f")
        self.edges["f"](y - r)
        self.corner(90, r)

        self.move(tw, th, move, label=label)

    def Uwall(self, x, y, h, r, edges="ee", move=None, label=""):
        e = [self.edges.get(edge, edge) for edge in edges]

        w = self.edges["F"].spacing()
        cl = r * math.pi / 2

        tw = 2 * y + x - 4 * (cl - r) + e[0].spacing() + e[1].spacing()
        th = h + 2 * w
        if self.move(tw, th, move, True, label=label):
            return

        self.moveTo(e[0].spacing())

        for nr, flex in enumerate("XE"):
            self.edges["F"](y - r)
            if x - 2 * r > 0.1 * self.thickness:
                self.edges[flex](cl, h=th)
                self.edges["F"](x - 2 * r)
                self.edges[flex](cl, h=th)
            else:
                self.edges[flex](2 * cl + x - 2 * r, h=th)
            self.edges["F"](y - r)
            self.edgeCorner("F", e[nr])
            e[nr](h)
            self.edgeCorner(e[nr], "F")

        self.move(tw, th, move, label=label)

    def render(self):
        x, y, h, r = self.x, self.y, self.h, self.radius

        self.radius = r = min(r, x / 2.0, y)

        _ = self.translations.gettext
        t1, t2, t3, t4 = self.topEdges(self.top_edge)

        self.U(x, y, r, t1, move="right", label=_("left"))
        self.U(x, y, r, t3, move="up", label=_("right"))
        self.U(x, y, r, t3, move="left only")
        self.Uwall(x, y, h, r, [t2, t4], move="up", label=_("wall"))

        self.drawLid(x, h, self.top_edge)
        self.lid(x, h, self.top_edge)
