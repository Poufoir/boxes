# Copyright (C) 2013-2022 Florian Festi
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
from boxes.default_box import DefaultBoxes
from boxes import edges
from boxes.utils import edge_init


class BirdHouse(DefaultBoxes):
    """Simple Bird House"""

    ui_group = "Misc"

    def __init__(
        self,
        x: float = 200,
        y: float = 200,
        h: float = 200,
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
        roof_overhang: float = 0.4,
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
        # overhang as fraction of the roof length
        self.roof_overhang = roof_overhang
        # finger=10.0, space=10.0
        edge_init(self, [edges.FingerJointSettings])

    def side(self, x, h, edges="hfeffef", callback=None, move=None):
        angles = (90, 0, 45, 90, 45, 0, 90)
        roof = 2**0.5 * x / 2
        t = self.thickness
        lengths = (x, h, t, roof, roof, t, h)

        edges = [self.edges.get(e, e) for e in edges]
        edges.append(edges[0])  # wrap around

        tw = x + edges[1].spacing() + edges[-2].spacing()
        th = (
            h
            + x / 2
            + t
            + edges[0].spacing()
            + max(edges[3].spacing(), edges[4].spacing())
        )

        if self.move(tw, th, move, True):
            return

        self.moveTo(edges[-2].spacing())
        for i in range(7):
            self.cc(callback, i, y=self.burn + edges[i].startwidth())
            edges[i](lengths[i])
            self.edgeCorner(edges[i], edges[i + 1], angles[i])

        self.move(tw, th, move)

    def roof(self, x, h, overhang, edges="eefe", move=None):
        t = self.thickness
        edges = [self.edges.get(e, e) for e in edges]

        tw = x + 2 * t + 2 * overhang + edges[1].spacing() + edges[3].spacing()
        th = h + 2 * t + overhang + edges[0].spacing() + edges[2].spacing()

        if self.move(tw, th, move, True):
            return

        self.moveTo(overhang + edges[3].spacing(), edges[0].margin())
        edges[0](x + 2 * t)
        self.corner(90, overhang)
        edges[1](h + 2 * t)
        self.edgeCorner(edges[1], edges[2])
        self.fingerHolesAt(overhang + 0.5 * t, edges[2].startwidth(), h, 90)
        self.fingerHolesAt(x + overhang + 1.5 * t, edges[2].startwidth(), h, 90)
        edges[2](x + 2 * t + 2 * overhang)
        self.edgeCorner(edges[2], edges[3])
        edges[3](h + 2 * t)
        self.corner(90, overhang)

        self.move(tw, th, move)

    def side_hole(self, width):
        self.rectangularHole(
            width / 2, self.h / 2, 0.75 * width, 0.75 * self.h, r=self.thickness
        )

    def render(self):
        x, y, h = self.x, self.y, self.h

        roof = 2**0.5 * x / 2
        overhang = roof * self.roof_overhang

        cbx = [lambda: self.side_hole(x)]
        cby = [lambda: self.side_hole(y)]

        self.side(x, h, callback=cbx, move="right")
        self.side(x, h, callback=cbx, move="right")
        self.rectangularWall(y, h, "hFeF", callback=cby, move="right")
        self.rectangularWall(y, h, "hFeF", callback=cby, move="right")
        self.rectangularWall(x, y, "ffff", move="right")
        self.edges["h"].settings.setValues(
            self.thickness, relative=False, edge_width=overhang
        )
        self.roof(y, roof, overhang, "eefe", move="right")
        self.roof(y, roof, overhang, "eeFe", move="right")
