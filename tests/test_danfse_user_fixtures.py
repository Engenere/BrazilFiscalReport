import pytest

from brazilfiscalreport.danfse import Danfse, DanfseConfig
from tests.conftest import assert_pdf_equal, get_pdf_output_path


@pytest.fixture
def load_danfse_custom(load_xml):
    def _load_danfse(filename, config=None, event_filename=None):
        xml_content = load_xml(f"danfse/{filename}")
        event_xml = load_xml(f"danfse/{event_filename}") if event_filename else None
        return Danfse(xml=xml_content, config=config, event_xml=event_xml)

    return _load_danfse


def test_danfse_user_fixture_6187(tmp_path, load_danfse_custom):
    """DANFSe a partir de XML real (anonimizado) de suporte técnico."""
    danfse = load_danfse_custom("6187ae43-fd6b-4819-8e9e-9a0911eceec3.xml")
    expected_path = get_pdf_output_path("danfse", "danfse_user_6187")
    assert_pdf_equal(danfse, expected_path, tmp_path)


def test_danfse_user_fixture_661a(tmp_path, load_danfse_custom):
    """DANFSe a partir de XML real (anonimizado) com tomador pessoa física."""
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
    NFS-e), não é uma NFS-e. O DANFSe não deve ser gerado a partir dele
    como documento principal; o parser levanta ValueError.
    """
    with pytest.raises(ValueError, match="evento"):
        load_danfse_custom("5e6ca60e-7148-4d44-8bd8-d3aff2a6c16f_cancel.xml")


def test_danfse_associa_evento_cancelamento(load_danfse_custom):
    """NFS-e + evento de cancelamento -> situação Cancelada.

    A NFS-e (nº 242) é imutável (cStat 107). Associando o evento de
    cancelamento (que a referencia pela chave), a situação passa a
    Cancelada e a marca d'água é aplicada.
    """
    danfse = load_danfse_custom(
        "nfse_cancelada_242.xml",
        event_filename="5e6ca60e-7148-4d44-8bd8-d3aff2a6c16f_cancel.xml",
    )
    assert danfse.data["is_cancelled"] is True
    assert danfse.data["situacao_nfse"] == "Cancelada"


def test_danfse_sem_evento_permanece_autorizada(load_danfse_custom):
    """Sem o evento associado, a NFS-e nº 242 permanece Autorizada."""
    danfse = load_danfse_custom("nfse_cancelada_242.xml")
    assert danfse.data["is_cancelled"] is False
    assert danfse.data["situacao_nfse"] == "Autorizada"


def test_danfse_evento_chave_divergente_ignorado(load_danfse_custom):
    """Evento cujo chNFSe não bate com a NFS-e não altera a situação."""
    danfse = load_danfse_custom(
        "real_nfse.xml",  # chave diferente da do evento (nota 234 vs 242)
        event_filename="5e6ca60e-7148-4d44-8bd8-d3aff2a6c16f_cancel.xml",
    )
    assert danfse.data["is_cancelled"] is False
