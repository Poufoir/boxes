# Copyright (C) 2013-2020 Florian Festi
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
import math


class BottleStack(DefaultBoxes):
    """Stack bottles in a fridge"""

    description = """When rendered with the "double" option the parts with the double slots get connected the shorter beams in the asymmetrical slots.

Without the "double" option the stand is a bit more narrow.
"""

    ui_group = "Misc"

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
        diameter: float = 80,
        number: int = 3,
        depth: float = 80,
        double: bool = True,
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
        # diameter of the bottles in mm
        self.diameter = diameter
        # number of bottles to hold in the bottom row
        self.number = number
        # depth of the stand along the base of the bottles
        self.depth = depth
        # two pieces that can be combined to up to double the width
        self.double = double

    def front(self, h_sides, offset=0, move=None):
        t = self.thickness
        a = 60
        nr = self.number
        r1 = self.diameter / 2.0  # bottle
        r2 = r1 / math.cos(math.radians(90 - a)) - r1  # in between
        if self.double:
            r3 = 1.5 * t  # upper corners
        else:
            r3 = 0.5 * t
        h = (r1 + r2) * (1 - math.cos(math.radians(a)))
        h_extra = 1 * t
        h_s = h_sides - t
        p = 0.05 * t  # play

        tw, th = nr * r1 * 2 + 2 * r3, h + 2 * t

        if self.move(tw, th, move, True):
            return

        open_sides = r3 <= 0.5 * t

        if offset == 0:
            slot = [0, 90, h_s, -90, t, -90, h_s, 90]
            if open_sides:
                self.moveTo(0, h_s)
                self.polyline(r3 - 0.5 * t)
                self.polyline(*slot[4:])
            else:
                self.polyline(r3 - 0.5 * t)
                self.polyline(*slot)
            for i in range(nr - open_sides):
                self.polyline(2 * r1 - t)
                self.polyline(*slot)
            if open_sides:
                self.polyline(2 * r1 - t)
                self.polyline(*slot[:-3])
                self.polyline(r3 - 0.5 * t)
            else:
                self.polyline(r3 - 0.5 * t)
        else:
            slot = [0, 90, h_s, -90, t, -90, h_s, 90]
            h_s += t
            slot2 = [0, 90, h_s, -90, t + 2 * p, -90, h_s, 90]
            if open_sides:
                self.moveTo(0, h_s)
                self.polyline(t + p, -90, h_s, 90)
            else:
                self.polyline(r3 - 0.5 * t - p)
                self.polyline(*slot2)
            self.polyline(t - p)
            self.polyline(*slot)
            self.polyline(2 * r1 - 5 * t)
            self.polyline(*slot)
            self.polyline(t - p)
            self.polyline(*slot2)
            for i in range(1, nr - open_sides):
                self.polyline(2 * r1 - 3 * t - p)
                self.polyline(*slot)
                self.polyline(t - p)
                self.polyline(*slot2)
            if open_sides:
                self.polyline(2 * r1 - 3 * t - p)
                self.polyline(*slot)
                self.polyline(t - p)
                self.polyline(0, 90, h_s, -90, t + p)
            else:
                self.polyline(r3 - 0.5 * t - p)

        if open_sides:
            h_extra -= h_s

        self.polyline(0, 90, h_extra + h - r3, (90, r3))

        for i in range(nr):
            self.polyline(0, (a, r2), 0, (-2 * a, r1), 0, (a, r2))
        self.polyline(0, (90, r3), h_extra + h - r3, 90)

        self.move(tw, th, move)

    def side(self, l, h, short=False, move=None):
        t = self.thickness
        short = bool(short)

        tw, th = l + 2 * t - 4 * t * short, h

        if self.move(tw, th, move, True):
            return

        self.moveTo(t, 0)

        self.polyline(l - 3 * t * short)
        if short:
            end = [90, h - t, 90, t, -90, t, 90]
        else:
            end = [(90, t), h - 2 * t, (90, t), 0, 90, t, -90, t, -90, t, 90]
        self.polyline(0, *end)
        self.polyline(l - 2 * t - 3 * t * short)
        self.polyline(0, *reversed(end))

        self.move(tw, th, move)

    def render(self):
        t = self.thickness
        d = self.depth
        nr = self.number
        h_sides = 2 * t
        pieces = 2 if self.double else 1

        for offset in range(pieces):
            self.front(h_sides, offset, move="up")
            self.front(h_sides, offset, move="up")

        for short in range(pieces):
            for i in range(nr + 1):
                self.side(d, h_sides, short, move="up")
