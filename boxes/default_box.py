from boxes import Boxes, argparseSections, ArgparseEdgeType
from typing import Union, List

nema_sizes = {
    #    motor,flange, holes, screws
    8: (20.3, 16, 15.4, 3),
    11: (28.2, 22, 23, 4),
    14: (35.2, 22, 26, 4),
    16: (39.2, 22, 31, 4),
    17: (42.2, 22, 31, 4),
    23: (56.4, 38.1, 47.1, 5.2),
    24: (60, 36, 49.8, 5.1),
    34: (86.3, 73, 69.8, 6.6),
    42: (110, 55.5, 89, 8.5),
}


class DefaultBoxes(Boxes):
    def __init__(
        self,
        x: float = 100,
        y: float = 100,
        h: float = 100,
        sx: Union[str, List] = "50*3",
        sy: Union[str, List] = "50*3",
        sh: Union[str, List] = "50*3",
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
        self.x = x
        self.y = y
        self.h = h
        self.sx = sx
        self.sy = sy
        self.sh = sh
        self.hi = hi
        self.hole_dD = hole_dD
        self.bottom_edge = bottom_edge
        self.top_edge = top_edge
        self.outside = outside
        self.nema_mount = nema_mount
        super().__init__(
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

        for key in ("sx", "sy", "sh", "hole_dD"):
            default = getattr(self, key)
            if isinstance(default, str):
                result = argparseSections(default)
                setattr(self, key, result[0])
        for key, arg in {"bottom_edge": "Fhse", "top_edge": "efFhcESŠikvLtGyY"}.items():
            default = getattr(self, key)
            if isinstance(getattr(self, key), str):
                result = ArgparseEdgeType(arg)(default)
                setattr(self, key, result)
        if nema_mount not in nema_sizes:
            raise Exception(
                f"Problem with nema_mount, needed {list(nema_sizes.keys())}"
            )
