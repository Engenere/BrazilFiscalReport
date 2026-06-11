"""Configuração do DANFSe.

Mantém 100% de compatibilidade com a versão upstream (FontType Enum,
Margins, DecimalConfig, watermark_cancelled) e ACRESCENTA campos novos
necessários para a NT 008/009, todos com default que preserva o
comportamento atual.
"""

from dataclasses import dataclass, field
from enum import Enum
from numbers import Number
from typing import Optional


class FontType(Enum):
    COURIER = "Courier"
    TIMES = "Times"


@dataclass
class Margins:
    top: Number = 5
    right: Number = 5
    bottom: Number = 5
    left: Number = 5


@dataclass
class DecimalConfig:
    price_precision: int = 4
    quantity_precision: int = 4


@dataclass
class DanfseConfig:
    margins: Margins = field(default_factory=Margins)
    decimal_config: DecimalConfig = field(default_factory=DecimalConfig)
    font_type: FontType = FontType.TIMES
    watermark_cancelled: bool = False

    # --- NOVOS (NT 008/009) ---------------------------------------------
    # Exibir o canhoto/recibo (bloco opcional da NT 008).
    show_receipt: bool = False
    # Caminho para a TTF "Microsoft Sans Serif" (micross.ttf) exigida pela
    # NT 008 para o conteúdo. Se None, usa o fallback do font_type.
    # Elimina o hardcode de C:\\Windows\\Fonts\\micross.ttf.
    custom_font_path: Optional[str] = None
    custom_font_name: str = "micross"
