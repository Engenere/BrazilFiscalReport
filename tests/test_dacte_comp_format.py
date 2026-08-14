"""O valor de cada componente sai formatado em pt-BR, como o resto do DACTE.

O `vComp` era impresso cru do XML (`1234.56`) enquanto o VALOR TOTAL DO SERVIÇO
(`vTPrest`), desenhado na coluna ao lado do mesmo retângulo, já saía formatado
(`R$ 1.234,56`) — dois separadores decimais diferentes no mesmo quadro.
"""

import re
import zlib

import pytest

from brazilfiscalreport.dacte import Dacte


def textos_desenhados(pdf_bytes):
    """Todos os trechos de texto do content stream do PDF."""
    achados = []
    for bruto in re.findall(rb"stream\r?\n(.*?)endstream", pdf_bytes, re.S):
        try:
            fluxo = zlib.decompress(bruto.strip(b"\r\n")).decode("latin-1")
        except zlib.error:
            continue
        achados.extend(re.findall(r"Td\s*\((.*?)\)\s*Tj", fluxo))
    return achados


@pytest.fixture
def xml_dacte(load_xml):
    return load_xml("dacte/dacte_test_1.xml")


def dacte_com_componente(xml, valor):
    xml = re.sub(
        r"<Comp>.*?</Comp>",
        f"<Comp><xNome>FPESO</xNome><vComp>{valor}</vComp></Comp>",
        xml,
        count=1,
        flags=re.S,
    )
    return textos_desenhados(bytes(Dacte(xml=xml).output()))


def test_valor_do_componente_usa_separador_decimal_pt_br(xml_dacte):
    trechos = dacte_com_componente(xml_dacte, "331.77")

    assert "331,77" in trechos
    assert "331.77" not in trechos, "valor do componente saiu cru do XML"


def test_valor_do_componente_usa_separador_de_milhar(xml_dacte):
    """As fixtures só têm valores abaixo de 1000; o agrupamento fica sem cobertura."""
    trechos = dacte_com_componente(xml_dacte, "1234567.89")

    assert "1.234.567,89" in trechos
    assert "1234567.89" not in trechos


def test_componente_sem_valor_nao_quebra(xml_dacte):
    """format_number trata vazio como zero — o quadro não pode explodir."""
    xml = re.sub(
        r"<Comp>.*?</Comp>",
        "<Comp><xNome>FPESO</xNome><vComp></vComp></Comp>",
        xml_dacte,
        count=1,
        flags=re.S,
    )
    trechos = textos_desenhados(bytes(Dacte(xml=xml).output()))

    assert "FPESO" in trechos
    assert "0,00" in trechos
