from dataclasses import dataclass, field
from enum import Enum
from io import BytesIO
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
    # Logo do emitente, centralizada no topo do cupom.
    logo: str | BytesIO | bytes | None = None
    # Marca d'água "CANCELADA" sobre o cupom.
    watermark_cancelled: bool = False
    # Caractere que o emitente usa como quebra de linha dentro do infCpl
    # (";" e "|" são os usuais). Sem isso o texto sai como um bloco corrido.
    line_break_char: str | None = None
    # Largura da bobina em mm. 80 e 58 são os formatos usuais das
    # impressoras térmicas não fiscais.
    paper_width: Number = 80
    # Altura da página. O padrão (None) gera uma página única com a altura
    # exata do conteúdo, que é como a bobina contínua funciona. Fixar um
    # valor volta a quebrar o cupom em páginas desse tamanho.
    paper_height: Number | None = None
