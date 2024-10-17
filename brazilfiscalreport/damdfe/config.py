from dataclasses import dataclass, field
from enum import Enum
from io import BytesIO
from numbers import Number
from typing import Union


class FontType(Enum):
    COURIER = "Courier"
    TIMES = "Times"


@dataclass
class Margins:
    top: Number = 10
    right: Number = 10
    bottom: Number = 10
    left: Number = 10


@dataclass
class DecimalConfig:
    price_precision: int = 4
    quantity_precision: int = 4


class ReceiptPosition(Enum):
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"


@dataclass
class DamdfeConfig:
    logo: Union[str, BytesIO, bytes] = None
    margins: Margins = field(default_factory=Margins)
    receipt_pos: ReceiptPosition = ReceiptPosition.TOP
    decimal_config: DecimalConfig = field(default_factory=DecimalConfig)
    font_type: FontType = FontType.TIMES
