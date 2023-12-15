# Copyright (C) 2013-2018 Florian Festi
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


class AllEdges(DefaultBoxes):
    """Showing all edge types"""

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
        setting: Settings
        for setting in [
            edges.FingerJointSettings,
            edges.StackableSettings,
            edges.StackableSettings,
            edges.SlideOnLidSettings,
            edges.ClickSettings,
            edges.FlexSettings,
            edges.HandleEdgeSettings,
        ]:
            for key, arg in setting.get_arguments():
                setattr(self, key, arg)

    def render(self):
        x = self.x
        t = self.thickness

        chars = list(self.edges.keys())
        chars.sort(key=lambda c: c.lower() + (c if c.isupper() else ""))
        chars.reverse()

        self.moveTo(0, 10 * t)

        for c in chars:
            with self.saved_context():
                self.move(0, 0, "", True)
                self.moveTo(x, 0, 90)
                self.edge(t + self.edges[c].startwidth())
                self.corner(90)
                self.edges[c](x, h=4 * t)
                self.corner(90)
                self.edge(t + self.edges[c].endwidth())
                self.move(0, 0, "")

            self.moveTo(0, 3 * t + self.edges[c].spacing())
            self.text(f"{c} - {self.edges[c].description}")
            self.moveTo(0, 12 * t)
