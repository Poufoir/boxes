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
import math


class BreadBox(DefaultBoxes):
    """A BreadBox with a gliding door"""

    ui_group = "FlexBox"

    description = """Beware of the rolling shutter effect! Use wax on sliding surfaces.
"""

    def __init__(
        self,
        x: float = 150,
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
        radius: float = 40,
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
        # [surroundingspaces=0.5, (distance=0.75, connection=2.0)]
        edge_init(self, [edges.FingerJointSettings, edges.FlexSettings])
        # radius of the corners
        self.radius = radius

    def side(self, l, h, r, move=None):
        t = self.thickness

        if self.move(l + 2 * t, h + 2 * t, move, True):
            return

        self.moveTo(t, t)

        self.context.save()

        n = self.n
        a = 90.0 / n
        ls = 2 * math.sin(math.radians(a / 2)) * (r - 2.5 * t)

        self.fingerHolesAt(2 * t, 0, h - r, 90)
        self.moveTo(2.5 * t, h - r, 90 - a / 2)
        for i in range(n):
            self.fingerHolesAt(0, 0.5 * t, ls, 0)
            self.moveTo(ls, 0, -a)
        self.moveTo(0, 0, a / 2)
        self.fingerHolesAt(0, 0.5 * t, l / 2 - r, 0)
        self.context.restore()

        self.edges["f"](l)
        self.polyline(
            t,
            90,
            h - r,
            (90, r + t),
            l / 2 - r,
            90,
            t,
            -90,
            0,
        )
        self.edges["f"](l / 2)
        self.polyline(0, 90)
        self.edges["f"](h)

        self.move(l + 2 * t, h + 2 * t, move)

    def cornerRadius(self, r, two=False, move=None):
        s = self.spacing
        if self.move(r, r + s, move, True):
            return
        for i in range(2 if two else 1):
            self.polyline(r, 90, r, 180, 0, (-90, r), 0, -180)
            self.moveTo(r, r + s, 180)
        self.move(r, r + s, move)

    def rails(self, l, h, r, move=None):
        t = self.thickness
        s = self.spacing
        tw, th = l / 2 + 2.5 * t + 3 * s, h + 1.5 * t + 3 * s

        if self.move(tw, th, move, True):
            return

        self.moveTo(2.5 * t + s, 0)
        self.polyline(
            l / 2 - r,
            (90, r + t),
            h - r,
            90,
            t,
            90,
            h - r,
            (-90, r),
            l / 2 - r,
            90,
            t,
            90,
        )
        self.moveTo(-t - s, t + s)
        self.polyline(
            l / 2 - r,
            (90, r + t),
            h - r,
            90,
            t,
            90,
            h - r,
            (-90, r),
            l / 2 - r,
            90,
            t,
            90,
        )
        self.moveTo(+t - s, t + s)
        self.polyline(
            l / 2 - r,
            (90, r - 1.5 * t),
            h - r,
            90,
            t,
            90,
            h - r,
            (-90, r - 2.5 * t),
            l / 2 - r,
            90,
            t,
            90,
        )
        self.moveTo(-t - s, t + s)
        self.polyline(
            l / 2 - r,
            (90, r - 1.5 * t),
            h - r,
            90,
            t,
            90,
            h - r,
            (-90, r - 2.5 * t),
            l / 2 - r,
            90,
            t,
            90,
        )

        self.move(tw, th, move)

    def door(self, l, h, move=None):
        t = self.thickness
        if self.move(l, h, move, True):
            return
        self.fingerHolesAt(t, t, h - 2 * t)
        self.edge(2 * t)
        self.edges["X"](l - 2 * t, h)
        self.polyline(0, 90, h, 90, l, 90, h, 90)
        self.move(l, h, move)

    def render(self):
        x, y, h, r = self.x, self.y, self.h, self.radius
        self.n = n = 3

        if not r:
            self.radius = r = h / 2
        self.radius = r = min(r, h / 2)

        t = self.thickness
        self.context.save()
        self.side(x, h, r, move="right")
        self.side(x, h, r, move="right")
        self.rectangularWall(y, h, "fFfF", move="right")

        self.context.restore()
        self.side(x, h, r, move="up only")

        self.rectangularWall(x, y, "FEFF", move="right")
        self.rectangularWall(x / 2, y, "FeFF", move="right")

        self.door(
            x / 2 + h - 2 * r + 0.5 * math.pi * r + 2 * t, y - 0.2 * t, move="right"
        )

        self.rectangularWall(2 * t, y - 2.2 * t, edges="eeef", move="right")

        a = 90.0 / n
        ls = 2 * math.sin(math.radians(a / 2)) * (r - 2.5 * t)

        edges.FingerJointSettings(t, angle=a).edgeObjects(self, chars="aA")
        edges.FingerJointSettings(t, angle=a / 2).edgeObjects(self, chars="bB")

        self.rectangularWall(h - r, y, "fbfe", move="right")

        self.rectangularWall(ls, y, "fafB", move="right")

        for i in range(n - 2):
            self.rectangularWall(ls, y, "fafA", move="right")

        self.rectangularWall(ls, y, "fbfA", move="right")
        self.rectangularWall(x / 2 - r, y, "fefB", move="right")

        self.rails(x, h, r, move="right mirror")
        self.cornerRadius(r, two=True, move="right")
