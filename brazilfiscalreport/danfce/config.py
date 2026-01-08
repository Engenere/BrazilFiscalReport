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
    top: Number = 2
    right: Number = 2
    bottom: Number = 2
    left: Number = 2


@dataclass
class DecimalConfig:
    price_precision: int = 2
    quantity_precision: int = 3


@dataclass
class DanfceConfig:
    """
    Configurações do layout de DANFCe (cupom NFC-e).

    As margens e precisões padrão são pensadas para impressoras térmicas
    de 80mm, podendo ser sobrescritas conforme necessidade.
    """

    logo: Union[str, BytesIO, bytes] = None
    margins: Margins = field(default_factory=Margins)
    decimal_config: DecimalConfig = field(default_factory=DecimalConfig)
    font_type: FontType = FontType.TIMES
    watermark_cancelled: bool = False
