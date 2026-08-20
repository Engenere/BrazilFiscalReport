"""Componentes do valor da prestação além do 9º não podem sumir do DACTE.

O quadro "COMPONENTES DO VALOR DA PRESTAÇÃO DO SERVIÇO" é um retângulo fixo de
18 mm que comporta 3 colunas × 3 linhas. O XSD do CT-e define `Comp` como
`maxOccurs="unbounded"`, então um CT-e válido pode declarar mais de 9 — e o
excedente era descartado sem aviso, deixando a soma dos componentes exibidos
diferente do vTPrest impresso na coluna ao lado.
"""

import re
import zlib

import pytest

from brazilfiscalreport.dacte import Dacte
from brazilfiscalreport.dacte.dacte import to_float


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


def valor_impresso(texto):
    """Converte um valor como saiu no PDF ("1.740,00") em float, ou None.

    Os componentes são desenhados formatados em pt-BR, então ler o número de
    volta pede o caminho inverso — separador de milhar fora, vírgula por ponto.
    """
    if not re.fullmatch(r"\d{1,3}(?:\.\d{3})*,\d{2}", texto):
        return None
    return float(texto.replace(".", "").replace(",", "."))


@pytest.fixture
def xml_dacte(load_xml):
    return load_xml("dacte/dacte_test_1.xml")


def xml_com_componentes(xml, quantidade):
    """Substitui os componentes do XML por `quantidade` deles, de 10 em 10."""
    comps = "".join(
        f"<Comp><xNome>COMP {i}</xNome><vComp>{i * 10}.00</vComp></Comp>"
        for i in range(1, quantidade + 1)
    )
    return re.sub(r"<Comp>.*</Comp>", comps, xml, count=1, flags=re.S)


def test_componentes_alem_do_nono_aparecem_agregados(xml_dacte):
    """O bloco comporta 9 linhas; o excedente vira "DEMAIS" em vez de sumir."""
    xml = xml_com_componentes(xml_dacte, 12)
    trechos = textos_posicionados(bytes(Dacte(xml=xml).output()))
    texto = " ".join(t[2] for t in trechos)

    assert "DEMAIS" in texto, "o excedente de componentes sumiu do PDF"

    # Os 8 primeiros saem individualmente; do 9º ao 12º somam 90+100+110+120.
    assert "COMP 8" in texto
    assert "COMP 9" not in texto
    assert "420,00" in texto, "a linha agregada não preserva a soma do excedente"


def test_nove_componentes_saem_sem_agregacao(xml_dacte):
    """Exatamente 9 cabem no quadro: nada é agregado."""
    xml = xml_com_componentes(xml_dacte, 9)
    texto = " ".join(t[2] for t in textos_posicionados(bytes(Dacte(xml=xml).output())))

    assert "DEMAIS" not in texto
    for i in range(1, 10):
        assert f"COMP {i}" in texto


def test_soma_dos_componentes_exibidos_bate_com_o_total(xml_dacte):
    """A soma do que está impresso tem de fechar, com ou sem agregação."""
    for quantidade in (6, 9, 12, 20):
        xml = xml_com_componentes(xml_dacte, quantidade)
        trechos = textos_posicionados(bytes(Dacte(xml=xml).output()))
        rotulos = {t[2] for t in trechos}

        exibidos = [t for t in trechos if t[2].startswith("COMP ") or t[2] == "DEMAIS"]
        assert len(exibidos) == min(quantidade, 9), (
            f"{quantidade} componentes deveriam render "
            f"{min(quantidade, 9)} linhas, mas saíram {len(exibidos)}"
        )

        # As 3 colunas partilham a baseline, então cada linha do quadro é somada
        # uma vez só — daí o set de baselines em vez de iterar sobre os nomes.
        baselines = {y for y, _, _ in exibidos}
        valores = (valor_impresso(v) for y, _, v in trechos if y in baselines)
        total_exibido = sum(v for v in valores if v is not None)

        esperado = sum(i * 10 for i in range(1, quantidade + 1))
        assert total_exibido == esperado, (
            f"com {quantidade} componentes o PDF soma {total_exibido}, "
            f"mas o XML declara {esperado} (rótulos: {sorted(rotulos)[:5]})"
        )


def test_to_float_tolera_valor_ausente_ou_invalido():
    assert to_float("12.34") == 12.34
    assert to_float("") == 0.0
    assert to_float(None) == 0.0
    assert to_float("R$ 10") == 0.0
