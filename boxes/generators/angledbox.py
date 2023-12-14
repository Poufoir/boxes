# Copyright (C) 2013-2014 Florian Festi
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
from boxes.edges import Settings
import copy
from boxes.utils import edge_init


class AngledBox(DefaultBoxes):
    """Box with both ends cornered"""

    ui_group = "Box"

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
        n: int = 5,
        top: str = "none",
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
        # "number of walls at one side (1+)"
        self.n = n
        # style of the top and lid. One of :"none", "angled hole", "angled lid", "angled lid2"
        self.top = top
        edge_init(self, [edges.FingerJointSettings])

    def floor(self, x, y, n, edge="e", hole=None, move=None, callback=None, label=""):
        r, h, side = self.regularPolygon(2 * n + 2, h=y / 2.0)
        t = self.thickness

        if n % 2:
            lx = x - 2 * h + side
        else:
            lx = x - 2 * r + side

        edge = self.edges.get(edge, edge)

        tx = x + 2 * edge.spacing()
        ty = y + 2 * edge.spacing()

        if self.move(tx, ty, move, before=True):
            return

        self.moveTo((tx - lx) / 2.0, edge.margin())

        if hole:
            with self.saved_context():
                hr, hh, hside = self.regularPolygon(2 * n + 2, h=y / 2.0 - t)
                dx = side - hside
                hlx = lx - dx

                self.moveTo(dx / 2.0, t + edge.spacing())
                for i, l in enumerate(([hlx] + ([hside] * n)) * 2):
                    self.edge(l)
                    self.corner(360.0 / (2 * n + 2))

        for i, l in enumerate(([lx] + ([side] * n)) * 2):
            self.cc(callback, i, 0, edge.startwidth() + self.burn)
            edge(l)
            self.edgeCorner(edge, edge, 360.0 / (2 * n + 2))

        self.move(tx, ty, move, label=label)

    def render(self):
        x, y, h, n = self.x, self.y, self.h, self.n
        b = self.bottom_edge

        if n < 1:
            n = self.n = 1

        if x < y:
            x, y = y, x

        if self.outside:
            x = self.adjustSize(x)
            y = self.adjustSize(y)
            if self.top == "none":
                h = self.adjustSize(h, False)
            elif "lid" in self.top and self.top != "angled lid":
                h = self.adjustSize(h) - self.thickness
            else:
                h = self.adjustSize(h)

        r, hp, side = self.regularPolygon(2 * n + 2, h=y / 2.0)

        if n % 2:
            lx = x - 2 * hp + side
        else:
            lx = x - 2 * r + side

        fingerJointSettings = copy.deepcopy(self.edges["f"].settings)
        fingerJointSettings.setValues(self.thickness, angle=360.0 / (2 * (n + 1)))
        fingerJointSettings.edgeObjects(self, chars="gGH")

        with self.saved_context():
            if b != "e":
                self.floor(x, y, n, edge="f", move="right", label="Bottom")
            if self.top == "angled lid":
                self.floor(x, y, n, edge="e", move="right", label="Lower Lid")
                self.floor(x, y, n, edge="E", move="right", label="Upper Lid")
            elif self.top in ("angled hole", "angled lid2"):
                self.floor(
                    x, y, n, edge="F", move="right", hole=True, label="Top Rim and Lid"
                )
                if self.top == "angled lid2":
                    self.floor(x, y, n, edge="E", move="right", label="Upper Lid")
        self.floor(x, y, n, edge="F", move="up only")

        fingers = self.top in ("angled lid2", "angled hole")

        cnt = 0
        for j in range(2):
            cnt += 1
            if j == 0 or n % 2:
                self.rectangularWall(
                    lx,
                    h,
                    move="right",
                    edges=b + "GfG" if fingers else b + "GeG",
                    label=f"wall {cnt}",
                )
            else:
                self.rectangularWall(
                    lx,
                    h,
                    move="right",
                    edges=b + "gfg" if fingers else b + "geg",
                    label=f"wall {cnt}",
                )
            for i in range(n):
                cnt += 1
                if (i + j * ((n + 1) % 2)) % 2:  # reverse for second half if even n
                    self.rectangularWall(
                        side,
                        h,
                        move="right",
                        edges=b + "GfG" if fingers else b + "GeG",
                        label=f"wall {cnt}",
                    )
                else:
                    self.rectangularWall(
                        side,
                        h,
                        move="right",
                        edges=b + "gfg" if fingers else b + "geg",
                        label=f"wall {cnt}",
                    )
