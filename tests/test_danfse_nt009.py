"""Testes do DANFSe NT 008/009 (parser + smoke do renderer).

Formato pytest, alinhado às convenções do BrazilFiscalReport. Os fixtures
XML ficam em tests/fixtures/danfse/. Adapte os caminhos ao copiar para o
repositório (tests/ na raiz do projeto).
"""

import os

import pytest

from brazilfiscalreport.danfse import Danfse, DanfseConfig
from brazilfiscalreport.danfse.parser import DanfseParser

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "danfse")


def _xml(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def real_data():
    return DanfseParser(_xml("real_nfse.xml")).parse()


# -- NT 009 ---------------------------------------------------------------


def test_cnpj_alfanumerico(real_data):
    # CNPJ numérico do fixture real -> máscara padrão.
    assert real_data["issuer"]["id"] == "11.111.111/0001-11"


def test_cnpj_alfanumerico_tipo_c():
    xml = (
        '<NFSe xmlns="http://www.sped.fazenda.gov.br/nfse">'
        '<infNFSe Id="NFS1"><emit><CNPJ>12ABC34501DE35</CNPJ></emit></infNFSe>'
        "<DPS></DPS><valores></valores></NFSe>"
    )
    data = DanfseParser(xml).parse()
    assert data["issuer"]["id"] == "12.ABC.345/01DE-35"


def test_finalidade_traduzida(real_data):
    assert real_data["finalidade"] in ("Regular", "Crédito", "Débito")


def test_pais_iso2(real_data):
    assert real_data["service"]["country"] == "BR"


def test_pis_cofins_apos_2026_some():
    xml = (
        '<NFSe xmlns="http://www.sped.fazenda.gov.br/nfse">'
        '<infNFSe Id="NFS1"><cStat>100</cStat></infNFSe>'
        "<DPS><dCompet>2027-01-01</dCompet>"
        "<tribFed><piscofins><vPis>10</vPis><vCofins>20</vCofins>"
        "</piscofins></tribFed></DPS><valores></valores></NFSe>"
    )
    data = DanfseParser(xml).parse()
    assert data["federal_taxes"]["pis_debit"] == "-"


def test_money_duas_casas(real_data):
    # price_precision do config é 4, mas moeda deve sair com 2 casas.
    assert real_data["total_value"]["service_amount"] == "R$ 350,00"


def test_xml_minimo_nao_quebra():
    xml = (
        '<NFSe xmlns="http://www.sped.fazenda.gov.br/nfse">'
        '<infNFSe Id="NFS123"></infNFSe><DPS></DPS><valores></valores></NFSe>'
    )
    data = DanfseParser(xml).parse()
    assert data["taker"]["present"] is False


def test_chave_sem_prefixo_nfs(real_data):
    assert not real_data["key_nfse"].upper().startswith("NFS")


def test_complementary_info_transparencia(real_data):
    assert "Lei nº 12.741/2012" in real_data["complementary_info"]


# -- Renderer (smoke) -----------------------------------------------------


def test_render_pdf_ok(tmp_path):
    out = tmp_path / "danfse.pdf"
    doc = Danfse(_xml("real_nfse.xml"))
    doc.output(str(out))
    assert out.exists() and out.stat().st_size > 1000
    assert doc.pages_count == 1


def test_render_canhoto(tmp_path):
    out = tmp_path / "danfse_canhoto.pdf"
    doc = Danfse(_xml("real_nfse.xml"), DanfseConfig(show_receipt=True))
    doc.output(str(out))
    assert out.exists()


def test_render_cancelada_uma_pagina(tmp_path):
    out = tmp_path / "danfse_cancelada.pdf"
    doc = Danfse(_xml("real_nfse.xml"), DanfseConfig(watermark_cancelled=True))
    doc.output(str(out))
    assert doc.pages_count == 1


# -- IBS/CBS NT-004 (estrutura oficial aninhada) --------------------------


@pytest.fixture
def ibscbs_data():
    return DanfseParser(_xml("nfse_ibscbs.xml")).parse()


def test_ibscbs_presente(ibscbs_data):
    assert ibscbs_data["ibs_cbs_taxes"]["present"] is True


def test_ibscbs_cst_cclass(ibscbs_data):
    assert ibscbs_data["ibs_cbs_taxes"]["cst_cclass"] == "000 / 000001"


def test_ibscbs_valores_totalizadores(ibscbs_data):
    ic = ibscbs_data["ibs_cbs_taxes"]
    # totCIBS/gIBS/gIBSUFTot/vIBSUF e gIBSMunTot/vIBSMun
    assert ic["valor_apurado_est_ibs"] == "R$ 100,00"
    assert ic["valor_apurado_mun_ibs"] == "R$ 20,00"
    assert ic["valor_total_apurado_ibs"] == "R$ 120,00"
    # totCIBS/gCBS/vCBS
    assert ic["valor_total_apurado_cbs"] == "R$ 88,00"


def test_ibscbs_aliquotas(ibscbs_data):
    ic = ibscbs_data["ibs_cbs_taxes"]
    assert ic["aliq_ibs_uf_mun"] == "10,00% / 2,00%"
    assert ic["aliq_cbs"] == "8,80%"


def test_ibscbs_total_e_liquido(ibscbs_data):
    tv = ibscbs_data["total_value"]
    assert tv["total_ibs_cbs"] == "R$ 208,00"
    assert tv["net_value_ibs_cbs"] == "R$ 1.208,00"


def test_ibscbs_destinatario_distinto(ibscbs_data):
    rec = ibscbs_data["recipient"]
    assert rec["present"] is True
    assert rec["is_taker"] is False
    assert rec["name"] == "EMPRESA DESTINATARIA DISTINTA LTDA"
    assert rec["city"] == "São Paulo - SP"


def test_ibscbs_render_pdf(tmp_path):
    out = tmp_path / "danfse_ibscbs.pdf"
    doc = Danfse(_xml("nfse_ibscbs.xml"))
    doc.output(str(out))
    assert out.exists() and doc.pages_count == 1
