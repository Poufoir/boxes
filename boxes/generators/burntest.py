# Copyright (C) 2013-2019 Florian Festi
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
from boxes.Color import Color


class BurnTest(DefaultBoxes):
    """Test different burn values"""

    description = """This generator will make shapes that you can use to select
optimal value for burn parameter for other generators. After burning try to
attach sides with the same value and use best fitting one on real projects.
In this generator set burn in the Default Settings to the lowest value
to be tested. To get an idea cut a rectangle with known nominal size and
measure the shrinkage due to the width of the laser cut. Now you can
measure the burn value that you should use in other generators. It is half
the difference of the overall size as shrinkage is occurring on both
sides. You can use the reference rectangle as it is rendered without burn
correction.

See also LBeam that can serve as compact BurnTest and FlexTest for testing flex settings.
"""

    ui_group = "Part"

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
        step: float = 0.01,
        pairs: int = 2,
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
        # increases in burn value between the sides
        self.step = step
        # number of pairs (each testing four burn values)
        self.pairs = pairs

    def render(self):
        x, s = self.x, self.step
        t = self.thickness

        fsize = 12.5 * self.x / 100 if self.x < 81 else 10

        self.moveTo(t, t)

        for cnt in range(self.pairs):
            for i in range(4):
                self.text(
                    "%.3fmm" % self.burn,
                    x / 2,
                    t,
                    fontsize=fsize,
                    align="center",
                    color=Color.ETCHING,
                )
                self.edges["f"](x)
                self.corner(90)
                self.burn += s

            self.burn -= 4 * s

            self.moveTo(x + 2 * t + self.spacing, -t)
            for i in range(4):
                self.text(
                    "%.3fmm" % self.burn,
                    x / 2,
                    t,
                    fontsize=fsize,
                    align="center",
                    color=Color.ETCHING,
                )
                self.edges["F"](x)
                self.polyline(t, 90, t)
                self.burn += s
            self.moveTo(x + 2 * t + self.spacing, t)
