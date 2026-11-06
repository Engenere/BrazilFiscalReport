"""
DANFE Simplificado - Etiqueta (NT 2020.004 v1.10; MOC 7.0 Anexo II, item 3.12).
"""

import re

import pytest

from brazilfiscalreport.danfe import DanfeEtiqueta, DanfeEtiquetaConfig
from brazilfiscalreport.danfe.danfe_etiqueta import format_quantity
from tests.conftest import assert_pdf_equal, get_pdf_output_path


@pytest.fixture
def load_etiqueta(load_xml):
    def _load_etiqueta(filename, config=None):
        return DanfeEtiqueta(xml=load_xml(f"danfe/{filename}"), config=config)

    return _load_etiqueta


def epec_xml(load_xml):
    """nfe_test_1.xml issued in EPEC contingency, without the protocol."""
    xml = load_xml("danfe/nfe_test_1.xml").replace(
        "<tpEmis>1</tpEmis>", "<tpEmis>4</tpEmis>"
    )
    return re.sub(
        r"(<verProc>[^<]*</verProc>)",
        r"\1<dhCont>2020-01-01T11:30:00-03:00</dhCont>"
        r"<xJust>Falha de comunicacao com a SEFAZ autorizadora</xJust>",
        xml,
    )


def test_danfe_etiqueta_default(tmp_path, load_etiqueta):
    """Authorized NF-e in production, on the default 100 x 150 mm label."""
    etiqueta = load_etiqueta("nfe_with_production_environment.xml")
    pdf_path = get_pdf_output_path("danfe_etiqueta", "danfe_etiqueta_default")
    assert_pdf_equal(etiqueta, pdf_path, tmp_path)


def test_danfe_etiqueta_delivery_address(tmp_path, load_etiqueta):
    """
    With the entrega group the label carries the delivery address and the
    receiver; homologation and no protocol print "SEM VALOR FISCAL".
    """
    etiqueta = load_etiqueta("nfe_retirada_entrega.xml")
    title, address = etiqueta._delivery_address()
    assert title == "ENDEREÇO DE ENTREGA"
    assert address.startswith("ARMAZEM LOCAL DE ENTREGA LTDA - Avenida Brasil, 2000")
    assert address.endswith("São Paulo/SP - CEP 01430-000")
    pdf_path = get_pdf_output_path("danfe_etiqueta", "danfe_etiqueta_entrega")
    assert_pdf_equal(etiqueta, pdf_path, tmp_path)


def test_danfe_etiqueta_logo(tmp_path, load_etiqueta, logo_path):
    """The brand logo prints centered between the header and the issuer."""
    config = DanfeEtiquetaConfig(logo=logo_path)
    etiqueta = load_etiqueta("nfe_with_production_environment.xml", config=config)
    pdf_path = get_pdf_output_path("danfe_etiqueta", "danfe_etiqueta_logo")
    assert_pdf_equal(etiqueta, pdf_path, tmp_path)


def test_danfe_etiqueta_items(tmp_path, load_etiqueta):
    """The items that do not fit on the label are counted in the last line."""
    config = DanfeEtiquetaConfig(display_items=True)
    etiqueta = load_etiqueta("nfe_multi_page_products.xml", config=config)
    pdf_path = get_pdf_output_path("danfe_etiqueta", "danfe_etiqueta_itens")
    assert_pdf_equal(etiqueta, pdf_path, tmp_path)


def test_danfe_etiqueta_minimal(tmp_path, load_etiqueta):
    """Only the fields of the NT: no total (optional since v1.10), no address."""
    config = DanfeEtiquetaConfig(display_total=False, display_delivery_address=False)
    etiqueta = load_etiqueta("nfe_with_production_environment.xml", config=config)
    pdf_path = get_pdf_output_path("danfe_etiqueta", "danfe_etiqueta_minima")
    assert_pdf_equal(etiqueta, pdf_path, tmp_path)


def test_danfe_etiqueta_epec(tmp_path, load_xml):
    """EPEC: protocol of the event, start and reason of the contingency."""
    config = DanfeEtiquetaConfig(epec_protocol="891200000000001 - 01/01/2020 11:35:00")
    etiqueta = DanfeEtiqueta(xml=epec_xml(load_xml), config=config)
    assert etiqueta._protocol() == (
        "PROTOCOLO DE AUTORIZAÇÃO DO EPEC",
        "891200000000001 - 01/01/2020 11:35:00",
        1,
    )
    pdf_path = get_pdf_output_path("danfe_etiqueta", "danfe_etiqueta_epec")
    assert_pdf_equal(etiqueta, pdf_path, tmp_path)


def test_danfe_etiqueta_cancelled(tmp_path, load_etiqueta):
    config = DanfeEtiquetaConfig(watermark_cancelled=True)
    etiqueta = load_etiqueta("nfe_with_production_environment.xml", config=config)
    pdf_path = get_pdf_output_path("danfe_etiqueta", "danfe_etiqueta_cancelada")
    assert_pdf_equal(etiqueta, pdf_path, tmp_path)


def test_danfe_etiqueta_narrow_paper(tmp_path, load_etiqueta):
    """On 80 mm paper the title goes below the barcode."""
    config = DanfeEtiquetaConfig(paper_width=80, paper_height=170)
    etiqueta = load_etiqueta("nfe_with_production_environment.xml", config=config)
    pdf_path = get_pdf_output_path("danfe_etiqueta", "danfe_etiqueta_80mm")
    assert_pdf_equal(etiqueta, pdf_path, tmp_path)


def test_danfe_etiqueta_58mm_stacks_fields_and_warns(tmp_path, load_etiqueta):
    """
    On 58 mm paper each field gets its own row, and the barcode can't reach
    the 6 cm of the MOC.
    """
    config = DanfeEtiquetaConfig(paper_width=58, paper_height=200)
    with pytest.warns(UserWarning, match="below the 60 mm"):
        etiqueta = load_etiqueta("nfe_with_production_environment.xml", config)
    pdf_path = get_pdf_output_path("danfe_etiqueta", "danfe_etiqueta_58mm")
    assert_pdf_equal(etiqueta, pdf_path, tmp_path)


def test_danfe_etiqueta_minimum_paper_width(load_xml):
    xml = load_xml("danfe/nfe_with_production_environment.xml")
    with pytest.raises(ValueError, match="at least 55 mm"):
        DanfeEtiqueta(xml=xml, config=DanfeEtiquetaConfig(paper_width=50))


@pytest.mark.parametrize(
    "value, expected",
    [("1.0000", "1"), ("2.5000", "2,5"), ("1250.125", "1.250,125"), ("", "0")],
)
def test_format_quantity(value, expected):
    assert format_quantity(value) == expected
