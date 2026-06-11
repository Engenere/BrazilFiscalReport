"""
Configuração do DANFSe (port de DanfseConfig).

Mantém compatibilidade com o uso original (config.margins.left, etc.) mas
remove a dependência de fonte hardcoded do Windows (micross.ttf).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Margins:
    left: float = 5.0
    top: float = 5.0
    right: float = 5.0
    bottom: float = 5.0


@dataclass
class DecimalConfig:
    price_precision: int = 2
    quantity_precision: int = 4


@dataclass
class FontType:
    # Família padrão caso a fonte custom não esteja disponível.
    value: str = "helvetica"


@dataclass
class DanfseConfig:
    margins: Margins = field(default_factory=Margins)
    decimal_config: DecimalConfig = field(default_factory=DecimalConfig)
    font_type: FontType = field(default_factory=FontType)

    # Marca d'água de cancelamento.
    watermark_cancelled: bool = False

    # Exibir canhoto/recibo (bloco 9 da spec).
    show_receipt: bool = False

    # Caminho opcional para uma fonte TTF custom (substitui o micross.ttf
    # hardcoded do Windows). Se None, usa font_type.value.
    custom_font_path: str | None = None
    custom_font_name: str = "micross"
