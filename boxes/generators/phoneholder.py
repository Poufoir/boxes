# Copyright (C) 2021 Guillaume Collic
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

import math
from functools import partial
from typing import List, Union

from boxes import Boxes, edges
from boxes.default_box import DefaultBoxes
from boxes import edges
from boxes.utils import edge_init


class PhoneHolder(DefaultBoxes):
    """
    Smartphone desk holder
    """

    ui_group = "Misc"

    description = """
    This phone stand holds your phone between two tabs, with access to its
    bottom, in order to connect a charger, headphones, and also not to obstruct
    the mic.

    Default values are currently based on Galaxy S7.
"""

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
        phone_height: float = 142,
        phone_width: float = 73,
        phone_depth: float = 25,
        angle: float = 25,
        bottom_margin: float = 30,
        tab_size: float = 76,
        bottom_support_spacing: float = 16,
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
        self.phone_height = phone_height
        self.phone_width = phone_width
        # Depth of the phone. Used by the bottom support holding the
        # phone, and the side tabs depth as well. Should be at least
        # your material thickness for assembly reasons.
        self.phone_depth = phone_depth
        self.angle = angle
        # Height of the support below the phone
        self.bottom_margin = bottom_margin
        # Length of the tabs holding the phone
        self.tab_size = tab_size
        # Spacing between the two bottom support. Choose a value big
        # enough for the charging cable, without getting in the way of
        # other ports.
        self.bottom_support_spacing = bottom_support_spacing
        edge_init(self, [edges.FingerJointSettings])

    def render(self):
        self.h = self.phone_height + self.bottom_margin
        tab_start = self.bottom_margin
        tab_length = self.tab_size
        tab_depth = self.phone_depth
        support_depth = self.phone_depth
        support_spacing = self.bottom_support_spacing
        rad = math.radians(self.angle)
        self.stand_depth = self.h * math.sin(rad)
        self.stand_height = self.h * math.cos(rad)

        self.render_front_plate(tab_start, tab_length, support_spacing, move="right")

        self.render_back_plate(move="right")

        self.render_side_plate(tab_start, tab_length, tab_depth, move="right")

        for move in ["right mirror", "right"]:
            self.render_bottom_support(tab_start, support_depth, tab_length, move=move)

    def render_front_plate(
        self,
        tab_start,
        tab_length,
        support_spacing,
        support_fingers_length=None,
        move="right",
    ):
        if not support_fingers_length:
            support_fingers_length = tab_length

        be = BottomEdge(self, tab_start, support_spacing)
        se1 = SideEdge(self, tab_start, tab_length)
        se2 = SideEdge(self, tab_start, tab_length, reverse=True)
        self.rectangularWall(
            self.phone_width,
            self.h,
            [be, se1, "e", se2],
            move=move,
            callback=[
                partial(
                    lambda: self.front_plate_holes(
                        tab_start, support_fingers_length, support_spacing
                    )
                )
            ],
        )

    def render_back_plate(
        self,
        move="right",
    ):
        be = BottomEdge(self, 0, 0)
        self.rectangularWall(
            self.phone_width,
            self.stand_height,
            [be, "F", "e", "F"],
            move=move,
        )

    def front_plate_holes(
        self, support_start_height, support_fingers_length, support_spacing
    ):
        margin = (self.phone_width - support_spacing - self.thickness) / 2
        self.fingerHolesAt(
            margin,
            support_start_height,
            support_fingers_length,
        )
        self.fingerHolesAt(
            self.phone_width - margin,
            support_start_height,
            support_fingers_length,
        )

    def render_side_plate(self, tab_start, tab_length, tab_depth, move):
        te = TabbedEdge(self, tab_start, tab_length, tab_depth, reverse=True)
        self.rectangularTriangle(
            self.stand_depth,
            self.stand_height,
            ["e", "f", te],
            move=move,
            num=2,
        )

    def render_bottom_support(
        self, support_start_height, support_depth, support_fingers_length, move="right"
    ):
        full_height = support_start_height + support_fingers_length
        rad = math.radians(self.angle)
        floor_length = full_height * math.sin(rad)
        angled_height = full_height * math.cos(rad)
        bottom_radius = min(support_start_height, 3 * self.thickness + support_depth)
        smaller_radius = 0.5
        support_hook_height = 5
        full_width = floor_length + (support_depth + 3 * self.thickness) * math.cos(rad)
        if self.move(full_width, angled_height, move, True):
            return

        self.polyline(
            floor_length,
            self.angle,
            3 * self.thickness + support_depth - bottom_radius,
            (90, bottom_radius),
            support_hook_height + support_start_height - bottom_radius,
            (180, self.thickness),
            support_hook_height - smaller_radius,
            (-90, smaller_radius),
            self.thickness + support_depth - smaller_radius,
            -90,
        )
        self.edges["f"](support_fingers_length)
        self.polyline(
            0,
            180 - self.angle,
            angled_height,
            90,
        )
        # Move for next piece
        self.move(full_width, angled_height, move)


class BottomEdge(edges.BaseEdge):
    def __init__(self, boxes, support_start_height, support_spacing) -> None:
        super().__init__(boxes, None)
        self.support_start_height = support_start_height
        self.support_spacing = support_spacing

    def __call__(self, length, **kw):
        cable_hole_radius = 2.5
        self.support_spacing = max(self.support_spacing, 2 * cable_hole_radius)
        side = (length - self.support_spacing - 2 * self.thickness) / 2

        half = [
            side,
            90,
            self.support_start_height,
            -90,
            self.thickness,
            -90,
            self.support_start_height,
            90,
            self.support_spacing / 2 - cable_hole_radius,
            90,
            2 * cable_hole_radius,
        ]
        path = half + [(-180, cable_hole_radius)] + list(reversed(half))
        self.polyline(*path)


class SideEdge(edges.BaseEdge):
    def __init__(self, boxes, tab_start, tab_length, reverse=False) -> None:
        super().__init__(boxes, None)
        self.tab_start = tab_start
        self.tab_length = tab_length
        self.reverse = reverse

    def __call__(self, length, **kw):
        tab_start = self.tab_start
        tab_end = length - self.tab_start - self.tab_length

        if self.reverse:
            tab_start, tab_end = tab_end, tab_start

        self.edges["F"](tab_start)
        self.polyline(
            0,
            90,
            self.thickness,
            -90,
        )
        self.edges["f"](self.tab_length)
        self.polyline(0, -90, self.thickness, 90)
        self.edges["F"](tab_end)

    def startwidth(self) -> float:
        return self.boxes.thickness


class TabbedEdge(edges.BaseEdge):
    def __init__(self, boxes, tab_start, tab_length, tab_depth, reverse=False) -> None:
        super().__init__(boxes, None)
        self.tab_start = tab_start
        self.tab_length = tab_length
        self.tab_depth = tab_depth
        self.reverse = reverse

    def __call__(self, length, **kw):
        tab_start = self.tab_start
        tab_end = length - self.tab_start - self.tab_length

        if self.reverse:
            tab_start, tab_end = tab_end, tab_start

        self.edges["f"](tab_start)

        self.ctx.save()
        self.fingerHolesAt(0, -self.thickness / 2, self.tab_length, 0)
        self.ctx.restore()

        self.polyline(
            0,
            -90,
            self.thickness,
            (90, self.tab_depth),
            self.tab_length - 2 * self.tab_depth,
            (90, self.tab_depth),
            self.thickness,
            -90,
        )
        self.edges["f"](tab_end)

    def margin(self) -> float:
        return self.tab_depth + self.thickness
