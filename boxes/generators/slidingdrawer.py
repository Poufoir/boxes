from typing import List
from boxes.default_box import DefaultBoxes
from boxes import edges
from boxes.utils import edge_init


class SlidingDrawer(DefaultBoxes):
    """Sliding drawer box"""

    ui_group = "Box"

    def __init__(
        self,
        x: float = 60,
        y: float = 100,
        h: float = 30,
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
        play: float = 0.15,
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
        edge_init(
            self,
            [
                {
                    "setting": edges.FingerJointSettings,
                    "args": {"finger": 15.0, "space": 2.0},
                },
                {
                    "setting": edges.GroovedSettings,
                    "args": {"width": 0.4, "arc_angle": 100},
                },
            ],
        )
        # play between the two parts as multiple of the wall thickness
        self.play = play

    def render(self):
        x, y, h = self.x, self.y, self.h
        x = self.adjustSize(x)
        y = self.adjustSize(y)
        h = self.adjustSize(h)

        t = self.thickness
        p = self.play * t

        y = y + t
        if not self.outside:
            x = x + 4 * t + 2 * p
            y = y + 3 * t + 2 * p
            h = h + 3 * t + 2 * p

        x2 = x - (2 * t + 2 * p)
        y2 = y - (2 * t + 2 * p)
        h2 = h - (t + 2 * p)

        self.rectangularWall(x2, h2, "FFzF", label="in box wall", move="right")
        self.rectangularWall(y2, h2, "ffef", label="in box wall", move="up")
        self.rectangularWall(y2, h2, "ffef", label="in box wall")
        self.rectangularWall(x2, h2, "FFeF", label="in box wall", move="left up")
        self.rectangularWall(y2, x2, "FfFf", label="in box bottom", move="up")

        self.rectangularWall(y, x, "FFFe", label="out box bottom", move="right")
        self.rectangularWall(y, x, "FFFe", label="out box top", move="up")
        self.rectangularWall(y, h, "fffe", label="out box wall")
        self.rectangularWall(y, h, "fffe", label="out box wall", move="up left")

        self.rectangularWall(x, h, "fFfF", label="out box wall")
