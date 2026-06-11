"""
Geração e desenho do QR Code do DANFSe.

Reimplementação (o generate_qrcode.py original não foi fornecido). Usa a lib
`qrcode` para gerar a imagem em memória e a desenha no PDF FPDF2.

NT 008: o QR Code tem tamanho FIXO de 1,52 x 1,52 cm e aponta para o portal
nacional de consulta da NFS-e.
"""

from __future__ import annotations

import io

import qrcode

# Tamanho fixo exigido pela NT 008 (em mm).
QR_SIZE_MM = 15.2
# Posição sugerida pela norma (canto superior direito), em mm.
QR_X_MM = 174.8
QR_Y_MM = 16.7


def build_qr_url(key_nfse: str) -> str:
    """Monta a URL de consulta pública a partir da chave de acesso."""
    return (
        "https://www.nfse.gov.br/ConsultaPublica/"
        f"?tpc=1&chave={key_nfse}"
    )


def make_qr_image(data: str, box_size: int = 10, border: int = 2):
    """Gera um objeto PIL.Image do QR (corte de borda mínimo)."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("RGB")


def draw_qr_code(
    pdf,
    data: str,
    _unused=0,
    x: float = QR_X_MM,
    y: float = QR_Y_MM,
    size_mm: float = QR_SIZE_MM,
    box_size: int = 10,
    border: int = 2,
) -> None:
    """Desenha o QR Code no PDF.

    Assinatura compatível com o uso do código original
    ``draw_qr_code(self, qr_code, 0, num_x, num_y, box_size=..., border=...)``,
    porém com tamanho fixo da NT 008 por padrão.
    """
    img = make_qr_image(data, box_size=box_size, border=border)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    pdf.image(buffer, x=x, y=y, w=size_mm, h=size_mm)
