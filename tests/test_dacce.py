import pytest

from brazilfiscalreport.dacce import DaCCe
from tests.conftest import assert_pdf_equal, get_pdf_output_path


def test_dacce(tmp_path, load_xml, logo_path):
    emitente = {
        "nome": "EMPRESA LTDA",
        "end": "AV. TEST, 100",
        "bairro": "TEST",
        "cep": "88888-88",
        "cidade": "SÃO PAULO",
        "uf": "SP",
        "fone": "(11) 1234-5678",
    }
    xm_content = load_xml("dacce/xml_cce_1.xml")

    pdf_cce = DaCCe(xml=xm_content, emitente=emitente, image=logo_path)
    pdf_path = get_pdf_output_path("dacce", "cce")
    assert_pdf_equal(pdf_cce, pdf_path, tmp_path)


def test_dacce_without_emitente(tmp_path, load_xml):
    xm_content = load_xml("dacce/xml_cce_1.xml")

    pdf_cce = DaCCe(xml=xm_content)
    pdf_path = get_pdf_output_path("dacce", "cce_no_emitente")
    assert_pdf_equal(pdf_cce, pdf_path, tmp_path)


def test_dacce_cpf_recipient_and_issuer_ids(tmp_path, load_xml, logo_path):
    # Production event for an individual (CPFDest), issuer with the optional
    # CNPJ and IE keys: no watermark, "CPF Destinatário" and issuer ids.
    emitente = {
        "nome": "EMPRESA LTDA",
        "end": "AV. TEST, 100",
        "bairro": "TEST",
        "cidade": "SÃO PAULO",
        "uf": "SP",
        "fone": "(11) 1234-5678",
        "cnpj": "01234567890123",
        "ie": "123456789012",
    }
    xm_content = load_xml("dacce/xml_cce_cpf.xml")

    pdf_cce = DaCCe(xml=xm_content, emitente=emitente, image=logo_path)
    pdf_path = get_pdf_output_path("dacce", "cce_cpf")
    assert_pdf_equal(pdf_cce, pdf_path, tmp_path)


@pytest.mark.parametrize(
    "fixture",
    ["dacce/xml_cce_newlines_real.xml", "dacce/xml_cce_newlines_literal.xml"],
)
def test_dacce_correction_newlines(tmp_path, load_xml, fixture):
    # Real line breaks and a literal backslash + n (as some issuers send it)
    # must render the same: one line per line of the correction text.
    xm_content = load_xml(fixture)

    pdf_cce = DaCCe(xml=xm_content)
    pdf_path = get_pdf_output_path("dacce", "cce_newlines")
    assert_pdf_equal(pdf_cce, pdf_path, tmp_path)
