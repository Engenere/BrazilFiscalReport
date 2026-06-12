from dataclasses import dataclass, field
from enum import Enum
from numbers import Number


class FontType(Enum):
    COURIER = "Courier"
    TIMES = "Times"
    # Equivalente métrico da Arial exigida pela NT 008/2026 (fonte core do
    # PDF, dispensa embutir TTF).
    HELVETICA = "Helvetica"


@dataclass
class Margins:
    # NT 008/2026, item 2.2.2: margens entre 0,15 e 0,20 cm.
    top: Number = 2
    right: Number = 2
    bottom: Number = 2
    left: Number = 2


@dataclass
class DecimalConfig:
    # Campos monetários/alíquotas do leiaute v2.0 são 1-15V2/1-2V2 (2 casas).
    price_precision: int = 2
    quantity_precision: int = 2


@dataclass
class DanfseConfig:
    margins: Margins = field(default_factory=Margins)
    decimal_config: DecimalConfig = field(default_factory=DecimalConfig)
    font_type: FontType = FontType.HELVETICA
    watermark_cancelled: bool = False
    # Marca d'água "SUBSTITUÍDA" (NT 008/2026, item 2.5.2).
    watermark_replaced: bool = False
    # Bloco de canhoto na base do documento (NT 008/2026, item 2.1.13 e
    # Nota 11 — opcional).
    display_canhoto: bool = False
