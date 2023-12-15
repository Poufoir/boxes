# Copyright (C) 2013-2016 Florian Festi
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
import math
from boxes.utils import edge_init


class AngledCutJig(DefaultBoxes):  # Change class name!
    """Jig for making angled cuts in a laser cutter"""

    ui_group = "Misc"

    def __init__(
        self,
        x: float = 50,
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
        angle: float = 45,
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
        edge_init(self, [edges.FingerJointSettings])
        # Angle of the cut
        self.angle = angle

        # self.addSettingsArgs(edges.FingerJointSettings, surroundingspaces=1.0)

    def bottomCB(self):
        t = self.thickness
        self.fingerHolesAt(10 - t, 4.5 * t, 20, 0)
        self.fingerHolesAt(30 + t, 4.5 * t, self.x, 0)
        self.fingerHolesAt(10 - t, self.y - 4.5 * t, 20, 0)
        self.fingerHolesAt(30 + t, self.y - 4.5 * t, self.x, 0)

    def render(self):
        # adjust to the variables you want in the local scope
        x, y = self.x, self.y
        t = self.thickness

        th = x * math.tan(math.radians(90 - self.angle))
        l = (x**2 + th**2) ** 0.5
        th2 = 20 * math.tan(math.radians(self.angle))
        l2 = (20**2 + th2**2) ** 0.5

        self.rectangularWall(30 + x + 2 * t, y, callback=[self.bottomCB], move="right")
        self.rectangularWall(
            l,
            y,
            callback=[
                lambda: self.fingerHolesAt(0, 4.5 * t, l, 0),
                None,
                lambda: self.fingerHolesAt(0, 4.5 * t, l, 0),
                None,
            ],
            move="right",
        )
        self.rectangularWall(
            l2,
            y,
            callback=[
                lambda: self.fingerHolesAt(0, 4.5 * t, l2, 0),
                None,
                lambda: self.fingerHolesAt(0, 4.5 * t, l2, 0),
                None,
            ],
            move="right",
        )

        self.rectangularTriangle(x, th, "fef", num=2, move="up")
        self.rectangularTriangle(20, th2, "fef", num=2, move="up")
