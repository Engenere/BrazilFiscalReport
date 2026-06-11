import pytest

from brazilfiscalreport.danfse import Danfse, DanfseConfig
from tests.conftest import assert_pdf_equal, get_pdf_output_path


@pytest.fixture
def load_danfse_custom(load_xml):
    def _load_danfse(filename, config=None):
        xml_content = load_xml(f"danfse/{filename}")
        return Danfse(xml=xml_content, config=config)

    return _load_danfse


def test_danfse_user_fixture_6187(tmp_path, load_danfse_custom):
    """Teste com XML original de Suporte Técnico (Rogerio)."""
    danfse = load_danfse_custom("6187ae43-fd6b-4819-8e9e-9a0911eceec3.xml")
    expected_path = get_pdf_output_path("danfse", "danfse_user_6187")
    assert_pdf_equal(danfse, expected_path, tmp_path)


def test_danfse_user_fixture_661a(tmp_path, load_danfse_custom):
    """Teste com XML original de Clínica Médica (Belo Horizonte)."""
    danfse = load_danfse_custom("661a2f2b-6bdc-43df-a85d-57a8cc9f2658.xml")
    expected_path = get_pdf_output_path("danfse", "danfse_user_661a")
    assert_pdf_equal(danfse, expected_path, tmp_path)


def test_danfse_cancellation_watermark_with_real_xml(tmp_path, load_danfse_custom):
    """Teste de marca d'água de cancelamento com XML real."""
    config = DanfseConfig(watermark_cancelled=True)
    danfse = load_danfse_custom(
        "6187ae43-fd6b-4819-8e9e-9a0911eceec3.xml", config=config
    )
    expected_path = get_pdf_output_path("danfse", "danfse_cancelled_real")
    assert_pdf_equal(danfse, expected_path, tmp_path)


def test_danfse_event_xml_rejected(load_danfse_custom):
    """XML de evento (cancelamento) deve ser rejeitado com erro claro.

    O arquivo *_cancel.xml tem raiz <evento> (e101101 - Cancelamento de
    NFS-e), não é uma NFS-e. O DANFSe não deve ser gerado a partir dele;
    em vez de produzir um documento vazio, o parser levanta ValueError.
    """
    with pytest.raises(ValueError, match="evento"):
        load_danfse_custom("5e6ca60e-7148-4d44-8bd8-d3aff2a6c16f_cancel.xml")
