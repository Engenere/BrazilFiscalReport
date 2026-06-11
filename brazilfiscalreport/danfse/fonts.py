"""
Tipografia do DANFSe — conformidade com a NT 008/2026.

A NT 008 exige (seção 2.4 e seguintes):
    - Títulos e rótulos (labels): fonte ARIAL.
    - Conteúdo (valores): fonte MICROSOFT SANS SERIF.
    - Cor: preto sólido (K100).
    - Tamanhos mínimos:  labels 6-7pt | conteúdo 7pt | cabeçalho 8-9pt.
    - Linhas divisórias: 0,5pt | borda da página: 1pt.
    - Sombreamento: cinza claro 5% (RGB 242,242,242).

Estratégia de implementação no FPDF2
------------------------------------
- ARIAL: o FPDF2 mapeia "Arial" para a core font Helvetica (sem-serifa).
  Atende a norma para títulos/labels sem precisar de arquivo TTF.
- MICROSOFT SANS SERIF: NÃO é core font. Para conformidade total é preciso
  embarcar o arquivo TTF (micross.ttf). Quando ele não está disponível,
  caímos para Helvetica (também sem-serifa) para preservar a legibilidade.
  O caminho da TTF é configurável (DanfseConfig.custom_font_path), eliminando
  o hardcode de C:\\Windows\\Fonts\\micross.ttf do código original.

Toda a definição de família/estilo/tamanho fica AQUI, para que o renderer
nunca chame set_font com strings soltas — facilitando auditar a norma.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# Nomes lógicos usados internamente pelo renderer.
FONT_LABEL = "label"  # Arial  -> títulos e rótulos
FONT_VALUE = "value"  # MS Sans Serif -> conteúdo

# Cor preta sólida (K100) exigida pela norma.
COLOR_TEXT = (0, 0, 0)
# Sombreamento cinza 5%.
COLOR_SHADING = (242, 242, 242)

# Espessuras de linha (pt convertidos em mm: 1pt = 0.3528mm).
LINE_DIVIDER_MM = 0.5 * 0.3528  # 0,5pt
LINE_BORDER_MM = 1.0 * 0.3528  # 1pt


@dataclass(frozen=True)
class FontSpec:
    """Família + estilo + tamanho de um uso tipográfico."""

    family: str
    style: str  # "", "B", "I", "BI"
    size: int


class NT008Fonts:
    """Catálogo central de fontes do DANFSe conforme NT 008.

    Resolve a família real (Arial->helvetica; MS Sans Serif->micross ou
    fallback) e expõe presets de tamanho por contexto (label/valor/cabeçalho).
    """

    # Família base para labels: Arial == Helvetica core no FPDF2.
    LABEL_FAMILY = "helvetica"

    def __init__(
        self,
        pdf,
        custom_font_path: str | None = None,
        custom_font_name: str = "micross",
    ):
        self.pdf = pdf
        self.value_family = self._register_value_font(
            pdf, custom_font_path, custom_font_name
        )

    # -- registro -----------------------------------------------------------

    @staticmethod
    def _register_value_font(pdf, path: str | None, name: str) -> str:
        """Registra a fonte de conteúdo (MS Sans Serif) se a TTF existir.

        Retorna o nome de família a ser usado em set_font. Faz fallback para
        Helvetica quando a TTF não está disponível (mantém sem-serifa).
        """
        candidates = []
        if path:
            candidates.append(path)
        # Locais comuns (Windows e cópia local junto ao pacote).
        candidates.append(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "micross.ttf")
        )
        candidates.append(r"C:\Windows\Fonts\micross.ttf")

        for ttf in candidates:
            try:
                if ttf and os.path.exists(ttf):
                    pdf.add_font(name, style="", fname=ttf)
                    return name
            except Exception:
                continue
        # Fallback: Helvetica (sem-serifa, core).
        return "helvetica"

    # -- presets de tamanho (NT 008) ---------------------------------------

    def header_title(self) -> FontSpec:
        # "DANFSe v2.0" e título do cabeçalho (8-9pt, negrito).
        return FontSpec(self.LABEL_FAMILY, "B", 9)

    def block_title(self) -> FontSpec:
        # Título de bloco (ex.: "PRESTADOR / FORNECEDOR") — Arial bold 8pt.
        return FontSpec(self.LABEL_FAMILY, "B", 8)

    def label(self, size: int = 6) -> FontSpec:
        # Rótulo de campo — Arial 6-7pt. Default 6 (compacto), conforme original.
        return FontSpec(self.LABEL_FAMILY, "B", size)

    def value(self, size: int = 8) -> FontSpec:
        # Conteúdo — MS Sans Serif. Mínimo 7pt; original usa 8pt p/ valores.
        return FontSpec(self.value_family, "", size)

    def small(self) -> FontSpec:
        # Texto auxiliar (legenda do QR, ambiente) — 6/7pt.
        return FontSpec(self.value_family, "", 6)

    def warning(self) -> FontSpec:
        # "NFS-e SEM VALIDADE JURÍDICA" — Arial 9pt.
        return FontSpec(self.LABEL_FAMILY, "B", 9)

    # -- aplicação ----------------------------------------------------------

    def apply(self, spec: FontSpec) -> None:
        """Aplica um FontSpec ao PDF e garante cor preta (K100)."""
        self.pdf.set_font(spec.family, spec.style, spec.size)
        self.pdf.set_text_color(*COLOR_TEXT)
