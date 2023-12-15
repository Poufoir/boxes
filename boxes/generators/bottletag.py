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
import math


class BottleTag(DefaultBoxes):
    """Paper slip over bottle tag"""

    ui_group = "Misc"  # see ./__init__.py for names

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
        width: float = 70,
        height: float = 98,
        min_diameter: float = 24,
        max_diameter: float = 50,
        radius: float = 15,
        segment_width: int = 3,
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
        # width of neck tag
        self.width = width
        # height of neck tag
        self.height = height
        # inner diameter of bottle neck hole
        self.min_diameter = min_diameter
        # outer diameter of bottle neck hole
        self.max_diameter = max_diameter
        # corner radius of bottom tag
        self.radius = radius
        # inner segment width
        self.segment_width = segment_width

    def render(self):
        # adjust to the variables you want in the local scope
        width = self.width
        height = self.height
        r_min = self.min_diameter / 2
        r_max = self.max_diameter / 2
        r = self.radius
        segment_width = self.segment_width

        # tag outline
        self.moveTo(r)
        self.edge(width - r - r)
        self.corner(90, r)
        self.edge(height - width / 2.0 - r)
        self.corner(180, width / 2)
        self.edge(height - width / 2.0 - r)
        self.corner(90, r)

        # move to centre of hole and cut the inner circle
        self.moveTo(width / 2 - r, height - width / 2)
        with self.saved_context():
            self.moveTo(0, -r_min)
            self.corner(360, r_min)

        # draw the radial lines approx 2mm apart on r_min
        seg_angle = math.degrees(segment_width / r_min)
        # for neatness, we want an integral number of cuts
        num = math.floor(360 / seg_angle)
        for i in range(num):
            with self.saved_context():
                self.moveTo(0, 0, i * 360.0 / num)
                self.moveTo(r_min)
                self.edge(r_max - r_min)
                # Add some right angle components to reduce tearing
                with self.saved_context():
                    self.moveTo(0, 0, 90)
                    self.edge(0.5)
                with self.saved_context():
                    self.moveTo(0, 0, -90)
                    self.edge(0.5)
