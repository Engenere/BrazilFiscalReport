"""Textos longos no DACTE não podem invadir o campo vizinho.

O layout do DACTE é de posição absoluta: o endereço do emitente e o valor de cada
componente são desenhados em coordenadas fixas. Sem recorte, um texto mais largo
que a coluna é escrito por cima do vizinho e o PDF sai ilegível nesse ponto.

Estes testes renderizam o PDF e leem de volta as posições do texto — medem o
resultado, e não a chamada de um helper.
"""

import re
import zlib

import pytest

from brazilfiscalreport.dacte import Dacte

# 60 caracteres = limite de xNome no leiaute do CT-e.
RAZAO_SOCIAL_LONGA = "TRANSPORTADORA RODOVIARIA DE CARGAS GERAIS DO BRASIL SA ME"


def textos_posicionados(pdf_bytes):
    """[(y, x, texto)] de cada trecho desenhado, lendo o content stream do PDF."""
    achados = []
    for bruto in re.findall(rb"stream\r?\n(.*?)endstream", pdf_bytes, re.S):
        try:
            fluxo = zlib.decompress(bruto.strip(b"\r\n")).decode("latin-1")
        except zlib.error:
            continue
        for td_x, td_y, texto in re.findall(
            r"([\d.-]+)\s+([\d.-]+)\s+Td\s*\((.*?)\)\s*Tj", fluxo
        ):
            achados.append((round(float(td_y), 2), round(float(td_x), 2), texto))
    return achados


def mesma_linha(a, b, tolerancia=0.5):
    """Dois trechos partilham a baseline (a menos de `tolerancia`)?"""
    return abs(a[0] - b[0]) < tolerancia


@pytest.fixture
def xml_dacte(load_xml):
    return load_xml("dacte/dacte_test_1.xml")


def test_razao_social_longa_nao_escreve_por_cima_do_cnpj(xml_dacte):
    """O endereço é desenhado em Y fixo logo abaixo do nome.

    Se o nome ocupar duas linhas, a segunda cai exatamente sobre a linha
    "CNPJ: ... IE: ...", deixando ambas ilegíveis.
    """
    xml = xml_dacte.replace(
        "<xNome>FANTASMA TRANSPORTES LTDA</xNome>",
        f"<xNome>{RAZAO_SOCIAL_LONGA}</xNome>",
        1,
    )
    trechos = textos_posicionados(bytes(Dacte(xml=xml).output()))

    linhas_cnpj = [t for t in trechos if t[2].startswith("CNPJ:")]
    assert linhas_cnpj, "linha do CNPJ do emitente não encontrada no PDF"

    for cnpj in linhas_cnpj:
        vizinhos = [t for t in trechos if t is not cnpj and mesma_linha(t, cnpj)]
        assert not vizinhos, f"texto sobreposto à linha do CNPJ: {vizinhos}"


def test_nome_de_componente_longo_nao_invade_a_coluna_do_valor(xml_dacte):
    """Nome de componente largo é escrito por cima do valor à direita.

    "OUTROS VALORES" mede 25,01 mm; a coluna do nome tem 21,75 mm úteis.
    """
    xml = re.sub(
        r"<Comp>\s*<xNome>[^<]*</xNome>",
        "<Comp><xNome>OUTROS VALORES</xNome>",
        xml_dacte,
        count=1,
    )
    dacte = Dacte(xml=xml)
    trechos = textos_posicionados(bytes(dacte.output()))

    # O nome sai recortado ("OUTROS VAL..."), então procura-se pelo prefixo.
    nomes = [t for t in trechos if t[2].startswith("OUTROS")]
    assert nomes, "componente 'OUTROS VALORES' não encontrado no PDF"

    dacte.set_font(dacte.default_font, "", 8)
    col_width = (dacte.epw - 2 * dacte.l_margin) / 4
    largura_coluna_nome = col_width / 2

    for nome in nomes:
        largura = dacte.get_string_width(nome[2])
        assert largura <= largura_coluna_nome, (
            f"'{nome[2]}' ocupa {largura:.2f} mm numa coluna de "
            f"{largura_coluna_nome:.2f} mm — invade o valor à direita"
        )
