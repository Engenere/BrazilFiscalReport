import pytest

from brazilfiscalreport.damdfe import (
    Damdfe,
    DamdfeConfig,
    Margins,
)
from tests.conftest import assert_pdf_equal, get_pdf_output_path


@pytest.fixture
def load_damdfe(load_xml):
    def _load_damdfe(filename, config=None):
        xml_content = load_xml(f"damdfe/{filename}")
        return Damdfe(xml=xml_content, config=config)

    return _load_damdfe


def test_damdfe_default(tmp_path, load_damdfe):
    damdfe = load_damdfe("mdf-e_test_1.xml")
    pdf_path = get_pdf_output_path("damdfe", "damdfe_default")
    assert_pdf_equal(damdfe, pdf_path, tmp_path)


def test_damdfe_default_logo(tmp_path, load_damdfe, logo_path):
    damdfe_config = DamdfeConfig(
        logo=logo_path,
    )
    damdfe = load_damdfe("mdf-e_test_1.xml", config=damdfe_config)
    pdf_path = get_pdf_output_path("damdfe", "damdfe_default_logo")
    assert_pdf_equal(damdfe, pdf_path, tmp_path)


def test_damdfe_default_logo_margins(tmp_path, load_damdfe, logo_path):
    damdfe_config = DamdfeConfig(
        logo=logo_path,
        margins=Margins(top=10, right=10, bottom=10, left=10),
    )
    damdfe = load_damdfe("mdf-e_test_1.xml", config=damdfe_config)
    pdf_path = get_pdf_output_path("damdfe", "damdfe_default_logo_margins")
    assert_pdf_equal(damdfe, pdf_path, tmp_path)


def test_damdfe_no_authorization(tmp_path, load_damdfe):
    damdfe = load_damdfe("mdf-e_test_2.xml")
    pdf_path = get_pdf_output_path("damdfe", "damdfe_no_authorization")
    assert_pdf_equal(damdfe, pdf_path, tmp_path)


def test_damdfe_modal_aereo(tmp_path, load_damdfe, logo_path):
    damdfe_config = DamdfeConfig(
        logo=logo_path,
    )
    damdfe = load_damdfe("mdf-e_test_aereo.xml", config=damdfe_config)
    pdf_path = get_pdf_output_path("damdfe", "damdfe_aereo")
    assert_pdf_equal(damdfe, pdf_path, tmp_path)


def test_damdfe_default_cte(tmp_path, load_damdfe):
    damdfe = load_damdfe("mdf-e_test_3_cte.xml")
    pdf_path = get_pdf_output_path("damdfe", "damdfe_default_cte")
    assert_pdf_equal(damdfe, pdf_path, tmp_path)


def test_damdfe_aereo_contingencia(tmp_path, load_damdfe):
    damdfe = load_damdfe("mdf-e_test_aereo_contingencia.xml")
    pdf_path = get_pdf_output_path("damdfe", "damdfe_aereo_contingencia")
    assert_pdf_equal(damdfe, pdf_path, tmp_path)


def test_damdfe_default_ferroviario(tmp_path, load_damdfe):
    damdfe = load_damdfe("mdf-e_test_ferroviario.xml")
    pdf_path = get_pdf_output_path("damdfe", "damdfe_ferroviario")
    assert_pdf_equal(damdfe, pdf_path, tmp_path)


def test_damdfe_default_aquaviario(tmp_path, load_damdfe):
    damdfe = load_damdfe("mdf-e_test_aquaviario.xml")
    pdf_path = get_pdf_output_path("damdfe", "damdfe_aquaviario")
    assert_pdf_equal(damdfe, pdf_path, tmp_path)


def test_damdfe_multi_municipio(tmp_path, load_damdfe):
    damdfe = load_damdfe("mdf-e_test_multi_municipio.xml")
    pdf_path = get_pdf_output_path("damdfe", "damdfe_multi_municipio")
    assert_pdf_equal(damdfe, pdf_path, tmp_path)


def test_damdfe_origem_destino_prestacao(tmp_path, load_damdfe):
    damdfe_config = DamdfeConfig(display_origem_destino_prestacao=True)
    damdfe = load_damdfe("mdf-e_test_1.xml", config=damdfe_config)
    pdf_path = get_pdf_output_path("damdfe", "damdfe_origem_destino_prestacao")
    assert_pdf_equal(damdfe, pdf_path, tmp_path)


def test_damdfe_cnpj_alfanumerico(tmp_path, load_damdfe):
    damdfe = load_damdfe("mdf-e_cnpj_alfanumerico.xml")
    pdf_path = get_pdf_output_path("damdfe", "damdfe_cnpj_alfanumerico")
    assert_pdf_equal(damdfe, pdf_path, tmp_path)
