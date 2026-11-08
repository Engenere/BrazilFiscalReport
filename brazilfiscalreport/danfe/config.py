from dataclasses import dataclass, field
from enum import Enum
from io import BytesIO
from numbers import Number


class TaxConfiguration(Enum):
    STANDARD_ICMS_IPI = "Standard ICMS and IPI"
    ICMS_ST = "ICMS ST only"
    WITHOUT_IPI = "Without IPI fields"


class InvoiceDisplay(Enum):
    DUPLICATES_ONLY = "Duplicatas Only"
    FULL_DETAILS = "Full Details"


class FontType(Enum):
    COURIER = "Courier"
    TIMES = "Times"


class FontSize(Enum):
    # Os valores a seguir são multiplicadores que ajustam o tamanho da fonte da DANFE.
    SMALL = 1.0
    BIG = 1.35


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


class DanfeLayout(Enum):
    # AUTO picks the layout in force on the NF-e issue date (dhEmi): MOC 7.0
    # before 2026-12-01, NT 2026.010 from then on.
    AUTO = "auto"
    MOC_7_0 = "moc_7_0"
    NT_2026_010 = "nt_2026_010"


class ReceiptPosition(Enum):
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"


@dataclass
class ProductDescriptionConfig:
    display_branch: bool = False
    display_anp: bool = False
    display_anvisa: bool = False
    branch_info_prefix: str = ""
    display_additional_info: bool = True
    display_xped: bool = False


@dataclass
class FooterStamp:
    logo: str | BytesIO | bytes | None = None
    text: str = ""
    height: Number = 5
    logo_max_width: Number = 20
    spacing: Number = 1


@dataclass
class DanfeConfig:
    logo: str | BytesIO | bytes = None
    margins: Margins = field(default_factory=Margins)
    receipt_pos: ReceiptPosition = ReceiptPosition.TOP
    carrier_receipt: bool = False
    decimal_config: DecimalConfig = field(default_factory=DecimalConfig)
    tax_configuration: TaxConfiguration = TaxConfiguration.STANDARD_ICMS_IPI
    invoice_display: InvoiceDisplay = InvoiceDisplay.FULL_DETAILS
    font_type: FontType = FontType.TIMES
    font_size: FontSize = FontSize.SMALL
    display_pis_cofins: bool = False
    watermark_cancelled: bool = False
    infcpl_semicolon_newline: bool = False
    product_description_config: ProductDescriptionConfig = field(
        default_factory=ProductDescriptionConfig
    )
    footer_stamp: FooterStamp = field(default_factory=FooterStamp)
    layout: DanfeLayout = DanfeLayout.AUTO


@dataclass
class DanfeEtiquetaConfig:
    # Etiqueta térmica de 100 x 150 mm, o formato usual das etiquetas de envio.
    # A norma só exige largura mínima de 55 mm (NT 2020.004).
    paper_width: Number = 100
    paper_height: Number = 150
    margins: Margins = field(
        default_factory=lambda: Margins(top=3, right=3, bottom=3, left=3)
    )
    font_type: FontType = FontType.TIMES
    logo: str | BytesIO | bytes | None = None
    logo_height: Number = 12
    # Opcional desde a NT 2020.004 v1.10.
    display_total: bool = True
    # O endereço do destinatário, ou o do grupo entrega quando existir.
    display_delivery_address: bool = True
    display_items: bool = False
    watermark_cancelled: bool = False
    # Na contingência EPEC, o protocolo do evento (nº e data/hora), que vem no
    # retorno do evento e não no XML da NF-e.
    epec_protocol: str = ""
