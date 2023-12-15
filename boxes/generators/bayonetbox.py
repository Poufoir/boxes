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

from typing import List, Union
from boxes.default_box import DefaultBoxes
from boxes import edges
from boxes.utils import edge_init


class BayonetBox(DefaultBoxes):
    """Round box made from layers with twist on top"""

    description = """Glue together - all outside rings to the bottom, all inside rings to the top."""
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
        diameter: float = 50,
        lugs: int = 10,
        alignment_pins: float = 1,
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
        # Diameter of the box in mm
        self.diameter = diameter
        # number of locking lugs
        self.lugs = lugs
        # diameter of the alignment pins
        self.alignment_pins = alignment_pins

    def alignmentHoles(self, inner=False, outer=False):
        d = self.diameter
        r = d / 2
        t = self.thickness
        p = 0.05 * t
        l = self.lugs

        a = 180 / l
        with self.saved_context():
            for i in range(3):
                if outer:
                    self.hole(r - t / 2, 0, d=self.alignment_pins)
                if inner:
                    self.hole(r - 2 * t - p, 0, d=self.alignment_pins)
                self.moveTo(0, 0, 360 / 3)

    def lowerLayer(self, asPart=False, move=None):
        d = self.diameter
        r = d / 2
        t = self.thickness
        p = 0.05 * t
        l = self.lugs

        a = 180 / l

        if asPart:
            if self.move(d, d, move, True):
                return
            self.moveTo(d / 2, d / 2)

        self.alignmentHoles(inner=True)
        self.hole(0, 0, r=d / 2 - 2.5 * t)
        self.moveTo(d / 2 - 1.5 * t, 0, -90)

        for i in range(l):
            self.polyline(
                0,
                (-4 / 3 * a, r - 1.5 * t),
                0,
                90,
                0.5 * t,
                -90,
                0,
                (-2 / 3 * a, r - t),
                0,
                -90,
                0.5 * t,
                90,
            )

        if asPart:
            self.move(d, d, move)

    def lowerCB(self):
        d = self.diameter
        r = d / 2
        t = self.thickness
        p = 0.05 * t
        l = self.lugs

        a = 180 / l

        self.alignmentHoles(outer=True)
        with self.saved_context():
            self.lowerLayer()

        self.moveTo(d / 2 - 1.5 * t + p, 0, -90)
        for i in range(l):
            self.polyline(
                0,
                (-2 / 3 * a, r - 1.5 * t + p),
                0,
                90,
                0.5 * t,
                -90,
                0,
                (-4 / 3 * a, r - t + p),
                0,
                -90,
                0.5 * t,
                90,
            )

    def upperCB(self):
        d = self.diameter
        r = d / 2
        t = self.thickness
        p = 0.05 * t
        l = self.lugs

        a = 180 / l

        self.hole(0, 0, r=d / 2 - 2.5 * t)
        self.hole(0, 0, r=d / 2 - 1.5 * t)
        self.alignmentHoles(inner=True, outer=True)
        self.moveTo(d / 2 - 1.5 * t, 0, -90)

        for i in range(l):
            self.polyline(
                0,
                (-1.3 * a, r - 1.5 * t + p),
                0,
                90,
                0.5 * t,
                -90,
                0,
                (-0.7 * a, r - t + p),
                0,
                -90,
                0.5 * t,
                90,
            )

    def render(self):
        d = self.diameter
        t = self.thickness
        p = 0.05 * t

        if not self.outside:
            self.diameter = d = d - 3 * t

        self.parts.disc(
            d, callback=lambda: self.alignmentHoles(outer=True), move="right"
        )
        self.parts.disc(
            d,
            callback=lambda: (
                self.alignmentHoles(outer=True),
                self.hole(0, 0, d / 2 - 1.5 * t),
            ),
            move="right",
        )
        self.parts.disc(d, callback=self.lowerCB, move="right")
        self.parts.disc(d, callback=self.upperCB, move="right")
        self.parts.disc(
            d, callback=lambda: self.alignmentHoles(inner=True), move="right"
        )
