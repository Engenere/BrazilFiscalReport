from dataclasses import dataclass, field
from enum import Enum
from numbers import Number


class FontType(Enum):
    COURIER = "Courier"
    TIMES = "Times"
    HELVETICA = "Helvetica"


@dataclass
class Margins:
    top: Number = 2
    right: Number = 2
    bottom: Number = 2
    left: Number = 2


@dataclass
class DecimalConfig:
    price_precision: int = 2
    quantity_precision: int = 2


@dataclass
class DanfceConfig:
    """
    Configurações do layout de DANFCe (cupom NFC-e).

    As margens e precisões padrão são pensadas para impressoras térmicas
    de 80mm, podendo ser sobrescritas conforme necessidade.
    """

    margins: Margins = field(default_factory=Margins)
    decimal_config: DecimalConfig = field(default_factory=DecimalConfig)
    font_type: FontType = FontType.TIMES
